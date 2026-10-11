"""일일 스냅샷 비교 (docs/ARCHITECTURE.md 4.1).

API는 거래 등록일을 주지 않는다(rgstDate 는 등기일). 그래서 매일 같은 (시군구, 계약월)을 받아
어제 없던 deal_key 가 나타난 날을 first_seen_date 로 기록한다. 과거로 소급할 수 없다.

- 처음 본 키            → event 'registered', first_seen_date = 오늘 (bootstrap 이면 NULL)
- 해제로 바뀐 키         → event 'cancelled'
- 이번에 안 보이는 키     → event 'disappeared' (정정·삭제로 추정. 지우지 않고 표시만 한다)
  deal_key 에 가격이 들어 있어 가격 정정은 'disappeared' + 'registered' 한 쌍으로 보인다.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from collector.sources.molit import Deal

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
  deal_key TEXT PRIMARY KEY, apt_seq TEXT, apt_name TEXT, region_code TEXT, contract_month TEXT,
  contract_date TEXT, area_m2 REAL, floor INTEGER, price_10k INTEGER, deal_type TEXT,
  is_cancelled INTEGER, cancel_date TEXT, rgst_date TEXT,
  first_seen_date TEXT, last_seen_date TEXT, disappeared INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS deal_events (
  deal_key TEXT, event TEXT, event_date TEXT);
"""


@dataclass(frozen=True)
class Event:
    deal_key: str
    event: str  # registered | cancelled | disappeared
    event_date: date


def keyed(deals: list[Deal]) -> dict[str, Deal]:
    """deal_key 에 같은 키 안의 순번(#n)을 붙인다.

    같은 단지·계약일·면적·층·가격의 별개 거래가 실제로 있다 (2026-09 강남 94건 중 키 93개, 송파 276건 중 123개).
    그대로 키로 쓰면 거래를 잃는다. 동일 키 안에서는 해제 건을 뒤로 보내 순번이 해제 여부에 흔들리지 않게 한다.
    """
    out: dict[str, Deal] = {}
    seen: dict[str, int] = {}
    for d in sorted(deals, key=lambda d: (d.deal_key, d.is_cancelled)):
        n = seen.get(d.deal_key, 0)
        seen[d.deal_key] = n + 1
        out[f"{d.deal_key}#{n}"] = d
    return out


def open_store(path: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def apply_snapshot(
    con: sqlite3.Connection,
    region_code: str,
    contract_month: str,
    deals: list[Deal],
    today: date,
    bootstrap: bool = False,
) -> list[Event]:
    """(시군구, 계약월) 스냅샷 1건을 저장소와 비교해 반영하고 이벤트를 돌려준다."""
    events: list[Event] = []
    seen = keyed(deals)
    known = {
        r[0]: bool(r[1])
        for r in con.execute(
            "SELECT deal_key, is_cancelled FROM deals WHERE region_code=? AND contract_month=?",
            (region_code, contract_month),
        )
    }
    for key, d in seen.items():
        if key not in known:
            con.execute(
                "INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                (key, d.apt_seq, d.apt_name, region_code, contract_month, d.contract_date.isoformat(),
                 d.area_m2, d.floor, d.price_10k, d.deal_type, int(d.is_cancelled),
                 d.cancel_date.isoformat() if d.cancel_date else None,
                 d.rgst_date.isoformat() if d.rgst_date else None,
                 None if bootstrap else today.isoformat(), today.isoformat()),
            )
            if not bootstrap:
                events.append(Event(key, "registered", today))
            if d.is_cancelled and not bootstrap:
                events.append(Event(key, "cancelled", today))
        else:
            con.execute("UPDATE deals SET last_seen_date=?, disappeared=0, rgst_date=? WHERE deal_key=?",
                        (today.isoformat(), d.rgst_date.isoformat() if d.rgst_date else None, key))
            if d.is_cancelled and not known[key]:
                con.execute("UPDATE deals SET is_cancelled=1, cancel_date=? WHERE deal_key=?",
                            (d.cancel_date.isoformat() if d.cancel_date else None, key))
                events.append(Event(key, "cancelled", today))
    for key in known.keys() - seen.keys():
        if con.execute("SELECT disappeared FROM deals WHERE deal_key=?", (key,)).fetchone()[0] == 0:
            con.execute("UPDATE deals SET disappeared=1 WHERE deal_key=?", (key,))
            events.append(Event(key, "disappeared", today))
    con.executemany("INSERT INTO deal_events VALUES (?,?,?)",
                    [(e.deal_key, e.event, e.event_date.isoformat()) for e in events])
    con.commit()
    return events
