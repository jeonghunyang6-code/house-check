"""스냅샷 반영의 Postgres 판 (collector/snapshot.py 의 SQLite 판과 같은 diff_snapshot 을 쓴다).

(종류, 시군구, 계약월) 1칸마다: 저장된 키를 읽고 → 비교 → 변경을 트랜잭션 하나의 SQL 로 보낸다.
쓰는 쪽은 작업 하나뿐이라는 전제(동시 실행 없음)다. 매매(trade)와 전월세(rent)는 표·열만 다르다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from collector.db import Db, lit, select
from collector.snapshot import Diff, Event, diff_snapshot
from collector.sources.molit import Deal, Rent

CHUNK = 500


@dataclass(frozen=True)
class Kind:
    name: str  # snapshot_runs.kind
    table: str
    events: str
    key: str
    columns: tuple[str, ...]  # key·region_code·contract_month·first/last_seen 을 뺀 데이터 열
    values: Callable[[object], tuple]
    has_cancel: bool


TRADE = Kind(
    "trade", "deals", "deal_events", "deal_key",
    ("apt_seq", "apt_name", "contract_date", "area_m2", "floor", "price_10k", "deal_type", "is_cancelled",
     "cancel_date", "rgst_date"),
    lambda x: (x.apt_seq, x.apt_name, x.contract_date, x.area_m2, x.floor, x.price_10k, x.deal_type,
               x.is_cancelled, x.cancel_date, x.rgst_date),
    True,
)
RENT = Kind(
    "rent", "rents", "rent_events", "rent_key",
    ("apt_seq", "apt_name", "contract_date", "area_m2", "floor", "deposit_10k", "monthly_rent_10k",
     "contract_type", "used_renewal_right", "term_start", "term_end", "pre_deposit_10k", "pre_monthly_rent_10k"),
    lambda x: (x.apt_seq, x.apt_name, x.contract_date, x.area_m2, x.floor, x.deposit_10k, x.monthly_rent_10k,
               x.contract_type, x.used_renewal_right, x.term_start, x.term_end, x.pre_deposit_10k,
               x.pre_monthly_rent_10k),
    False,
)
KINDS = {"trade": TRADE, "rent": RENT}


def _chunks(xs: list, n: int = CHUNK):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def load_known(db: Db, k: Kind, region_code: str, contract_month: str) -> dict[str, tuple[bool, bool]]:
    cancel = "is_cancelled" if k.has_cancel else "FALSE AS is_cancelled"
    rows = select(
        db,
        f"SELECT {k.key} AS key, {cancel}, disappeared FROM {k.table} "
        f"WHERE region_code = {lit(region_code)} AND contract_month = {lit(contract_month)}",
    )
    return {r["key"]: (bool(r["is_cancelled"]), bool(r["disappeared"])) for r in rows}


def build_sql(
    k: Kind, region_code: str, contract_month: str, n_rows: int, d: Diff, today: date, bootstrap: bool
) -> str:
    stmts: list[str] = ["BEGIN;"]
    first_seen = None if bootstrap else today
    cols = (k.key, "region_code", "contract_month") + k.columns + ("first_seen_date", "last_seen_date")
    ins = [
        "(" + ", ".join(lit(v) for v in (key, region_code, contract_month, *k.values(x), first_seen, today)) + ")"
        for key, x in d.inserts.items()
    ]
    for part in _chunks(ins):
        stmts.append(f"INSERT INTO {k.table} ({', '.join(cols)}) VALUES\n" + ",\n".join(part) + ";")
    if k.has_cancel:
        seen = [f"({lit(key)}, {lit(x.rgst_date)})" for key, x in d.seen_again.items()]
        for part in _chunks(seen):
            stmts.append(
                f"UPDATE {k.table} AS t SET last_seen_date = {lit(today)}, disappeared = FALSE, rgst_date = v.rgst::date "
                "FROM (VALUES " + ", ".join(part) + f") AS v(k, rgst) WHERE t.{k.key} = v.k;"
            )
        canc = [f"({lit(key)}, {lit(x.cancel_date)})" for key, x in d.newly_cancelled.items()]
        for part in _chunks(canc):
            stmts.append(
                f"UPDATE {k.table} AS t SET is_cancelled = TRUE, cancel_date = v.cd::date "
                "FROM (VALUES " + ", ".join(part) + f") AS v(k, cd) WHERE t.{k.key} = v.k;"
            )
    else:
        for part in _chunks(list(d.seen_again)):
            stmts.append(
                f"UPDATE {k.table} SET last_seen_date = {lit(today)}, disappeared = FALSE "
                f"WHERE {k.key} IN (" + ", ".join(lit(x) for x in part) + ");"
            )
    for part in _chunks(d.disappeared):
        stmts.append(f"UPDATE {k.table} SET disappeared = TRUE WHERE {k.key} IN (" + ", ".join(lit(x) for x in part) + ");")
    ev = [f"({lit(e.deal_key)}, {lit(e.event)}, {lit(e.event_date)})" for e in d.events]
    for part in _chunks(ev):
        stmts.append(f"INSERT INTO {k.events} ({k.key}, event, event_date) VALUES " + ", ".join(part) + ";")
    cnt = {e: sum(x.event == e for x in d.events) for e in ("registered", "cancelled", "disappeared")}
    stmts.append(
        "INSERT INTO snapshot_runs (kind, region_code, contract_month, run_date, n_deals, n_registered, n_cancelled, "
        f"n_disappeared, bootstrap) VALUES ({lit(k.name)}, {lit(region_code)}, {lit(contract_month)}, {lit(today)}, "
        f"{n_rows}, {cnt['registered']}, {cnt['cancelled']}, {cnt['disappeared']}, {lit(bootstrap)}) "
        "ON CONFLICT (kind, region_code, contract_month, run_date) DO UPDATE SET n_deals = EXCLUDED.n_deals, "
        "n_registered = snapshot_runs.n_registered + EXCLUDED.n_registered, "
        "n_cancelled = snapshot_runs.n_cancelled + EXCLUDED.n_cancelled, "
        "n_disappeared = snapshot_runs.n_disappeared + EXCLUDED.n_disappeared;"
    )
    stmts.append("COMMIT;")
    return "\n".join(stmts)


def apply_snapshot_pg(
    db: Db, region_code: str, contract_month: str, rows: list[Deal] | list[Rent], today: date, bootstrap: bool,
    kind: Kind = TRADE,
) -> list[Event]:
    known = load_known(db, kind, region_code, contract_month)
    d = diff_snapshot(known, rows, today, bootstrap)
    db.query(build_sql(kind, region_code, contract_month, len(rows), d, today, bootstrap))
    return d.events


def should_bootstrap(db: Db, region_code: str, contract_month: str, today: date, kind: Kind = TRADE) -> bool:
    """처음 받는 칸일 때만 bootstrap 후보다. 그중
    - 그 시군구를 최근 3일(오늘 제외) 안에 받은 적이 없으면 bootstrap (첫 수집, 오래 끊긴 뒤 재개)
    - 그 시군구에서 이미 받은 가장 최근 달 이하이면 bootstrap (수집이 실패해 빠졌던 지난 칸)
    - 그 밖(새 달이 시작돼 처음 받는 칸)은 정상: 오늘 보이는 거래를 신규 등록으로 기록한다."""
    k, rc = lit(kind.name), lit(region_code)
    r = select(
        db,
        "SELECT "
        f"EXISTS (SELECT 1 FROM snapshot_runs WHERE kind = {k} AND region_code = {rc} "
        f"AND contract_month = {lit(contract_month)}) AS cell_seen, "
        f"EXISTS (SELECT 1 FROM snapshot_runs WHERE kind = {k} AND region_code = {rc} "
        f"AND run_date BETWEEN {lit(today)} - 3 AND {lit(today)} - 1) AS recent, "
        f"(SELECT max(contract_month) FROM snapshot_runs WHERE kind = {k} AND region_code = {rc}) AS max_month",
    )[0]
    if r["cell_seen"]:
        return False
    return not r["recent"] or (r["max_month"] is not None and contract_month <= r["max_month"])


def done_cells(db: Db, kind: Kind, regions: list[str], months: list[str]) -> set[tuple[str, str]]:
    """이미 한 번이라도 받은 (시군구, 계약월). 과거 이력 적재를 이어서 할 때 건너뛴다."""
    rows = select(
        db,
        f"SELECT DISTINCT region_code, contract_month FROM snapshot_runs WHERE kind = {lit(kind.name)} "
        f"AND region_code IN ({', '.join(lit(r) for r in regions)}) "
        f"AND contract_month IN ({', '.join(lit(m) for m in months)})",
    )
    return {(r["region_code"], r["contract_month"]) for r in rows}
