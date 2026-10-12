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


@dataclass
class Diff:
    """스냅샷 1건을 저장된 상태와 비교한 결과. 저장소(SQLite·Postgres)와 무관한 순수 계산."""
    inserts: dict[str, Deal]          # 처음 본 키
    seen_again: dict[str, Deal]       # 이미 있던 키 (last_seen·등기일 갱신, 사라짐 표시 해제)
    newly_cancelled: dict[str, Deal]  # 이미 있던 키 중 이번에 해제로 바뀐 것
    disappeared: list[str]            # 이번 응답에 없는 키 (처음 사라졌을 때만)
    events: list[Event]


def diff_snapshot(
    known: dict[str, tuple[bool, bool]],
    deals: list[Deal],
    today: date,
    bootstrap: bool = False,
    foreign: frozenset[str] = frozenset(),
) -> Diff:
    """known: deal_key → (is_cancelled, disappeared). 이벤트 순서는 SQLite 구현과 같다.

    foreign: 다른 (시군구, 계약월) 칸에 이미 저장된 키. 경계에 걸친 단지는 국토부가 두 시군구 응답에
    같은 거래를 모두 싣는다(예: 관악푸르지오 102동, 동작구·관악구). 먼저 받은 칸이 갖고 여기서는 건너뛴다.
    """
    seen = {k: v for k, v in keyed(deals).items() if k not in foreign}
    d = Diff({}, {}, {}, [], [])
    for key, deal in seen.items():
        if key not in known:
            d.inserts[key] = deal
            if not bootstrap:
                d.events.append(Event(key, "registered", today))
                if deal.is_cancelled:
                    d.events.append(Event(key, "cancelled", today))
        else:
            d.seen_again[key] = deal
            if deal.is_cancelled and not known[key][0]:
                d.newly_cancelled[key] = deal
                d.events.append(Event(key, "cancelled", today))
    for key in sorted(known.keys() - seen.keys()):
        if not known[key][1]:
            d.disappeared.append(key)
            d.events.append(Event(key, "disappeared", today))
    return d


def _iso(x: date | None) -> str | None:
    return x.isoformat() if x else None


def apply_snapshot(
    con: sqlite3.Connection,
    region_code: str,
    contract_month: str,
    deals: list[Deal],
    today: date,
    bootstrap: bool = False,
) -> list[Event]:
    """(시군구, 계약월) 스냅샷 1건을 SQLite 저장소와 비교해 반영하고 이벤트를 돌려준다 (테스트·로컬용)."""
    known = {
        r[0]: (bool(r[1]), bool(r[2]))
        for r in con.execute(
            "SELECT deal_key, is_cancelled, disappeared FROM deals WHERE region_code=? AND contract_month=?",
            (region_code, contract_month),
        )
    }
    d = diff_snapshot(known, deals, today, bootstrap)
    for key, x in d.inserts.items():
        con.execute(
            "INSERT INTO deals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
            (key, x.apt_seq, x.apt_name, region_code, contract_month, x.contract_date.isoformat(),
             x.area_m2, x.floor, x.price_10k, x.deal_type, int(x.is_cancelled),
             _iso(x.cancel_date), _iso(x.rgst_date), None if bootstrap else today.isoformat(), today.isoformat()),
        )
    for key, x in d.seen_again.items():
        con.execute("UPDATE deals SET last_seen_date=?, disappeared=0, rgst_date=? WHERE deal_key=?",
                    (today.isoformat(), _iso(x.rgst_date), key))
    for key, x in d.newly_cancelled.items():
        con.execute("UPDATE deals SET is_cancelled=1, cancel_date=? WHERE deal_key=?", (_iso(x.cancel_date), key))
    for key in d.disappeared:
        con.execute("UPDATE deals SET disappeared=1 WHERE deal_key=?", (key,))
    con.executemany("INSERT INTO deal_events VALUES (?,?,?)",
                    [(e.deal_key, e.event, e.event_date.isoformat()) for e in d.events])
    con.commit()
    return d.events
