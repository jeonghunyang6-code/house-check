"""스냅샷 반영의 Postgres 판 (collector/snapshot.py 의 SQLite 판과 같은 diff_snapshot 을 쓴다).

(시군구, 계약월) 1칸마다: 저장된 키를 읽고 → 비교 → 변경을 트랜잭션 하나의 SQL 로 보낸다.
쓰는 쪽은 일일 작업 하나뿐이라는 전제(동시 실행 없음)다.
"""

from __future__ import annotations

from datetime import date

from collector.db import Db, lit, select
from collector.snapshot import Diff, Event, diff_snapshot
from collector.sources.molit import Deal

CHUNK = 500


def _chunks(xs: list, n: int = CHUNK):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def load_known(db: Db, region_code: str, contract_month: str) -> dict[str, tuple[bool, bool]]:
    rows = select(
        db,
        "SELECT deal_key, is_cancelled, disappeared FROM deals "
        f"WHERE region_code = {lit(region_code)} AND contract_month = {lit(contract_month)}",
    )
    return {r["deal_key"]: (bool(r["is_cancelled"]), bool(r["disappeared"])) for r in rows}


def build_sql(
    region_code: str, contract_month: str, n_deals: int, d: Diff, today: date, bootstrap: bool
) -> str:
    stmts: list[str] = ["BEGIN;"]
    first_seen = None if bootstrap else today
    ins = [
        "(" + ", ".join(lit(v) for v in (
            key, x.apt_seq, x.apt_name, region_code, contract_month, x.contract_date, x.area_m2, x.floor,
            x.price_10k, x.deal_type, x.is_cancelled, x.cancel_date, x.rgst_date, first_seen, today,
        )) + ")"
        for key, x in d.inserts.items()
    ]
    for part in _chunks(ins):
        stmts.append(
            "INSERT INTO deals (deal_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, "
            "floor, price_10k, deal_type, is_cancelled, cancel_date, rgst_date, first_seen_date, last_seen_date) "
            "VALUES\n" + ",\n".join(part) + ";"
        )
    seen = [f"({lit(k)}, {lit(x.rgst_date)})" for k, x in d.seen_again.items()]
    for part in _chunks(seen):
        stmts.append(
            f"UPDATE deals AS t SET last_seen_date = {lit(today)}, disappeared = FALSE, rgst_date = v.rgst "
            "FROM (VALUES " + ", ".join(part) + ") AS v(k, rgst) WHERE t.deal_key = v.k;"
        )
    canc = [f"({lit(k)}, {lit(x.cancel_date)})" for k, x in d.newly_cancelled.items()]
    for part in _chunks(canc):
        stmts.append(
            "UPDATE deals AS t SET is_cancelled = TRUE, cancel_date = v.cd "
            "FROM (VALUES " + ", ".join(part) + ") AS v(k, cd) WHERE t.deal_key = v.k;"
        )
    for part in _chunks(d.disappeared):
        stmts.append("UPDATE deals SET disappeared = TRUE WHERE deal_key IN (" + ", ".join(lit(k) for k in part) + ");")
    ev = [f"({lit(e.deal_key)}, {lit(e.event)}, {lit(e.event_date)})" for e in d.events]
    for part in _chunks(ev):
        stmts.append("INSERT INTO deal_events (deal_key, event, event_date) VALUES " + ", ".join(part) + ";")
    cnt = {k: sum(e.event == k for e in d.events) for k in ("registered", "cancelled", "disappeared")}
    stmts.append(
        "INSERT INTO snapshot_runs (region_code, contract_month, run_date, n_deals, n_registered, n_cancelled, "
        f"n_disappeared, bootstrap) VALUES ({lit(region_code)}, {lit(contract_month)}, {lit(today)}, {n_deals}, "
        f"{cnt['registered']}, {cnt['cancelled']}, {cnt['disappeared']}, {lit(bootstrap)}) "
        "ON CONFLICT (region_code, contract_month, run_date) DO UPDATE SET n_deals = EXCLUDED.n_deals, "
        "n_registered = snapshot_runs.n_registered + EXCLUDED.n_registered, "
        "n_cancelled = snapshot_runs.n_cancelled + EXCLUDED.n_cancelled, "
        "n_disappeared = snapshot_runs.n_disappeared + EXCLUDED.n_disappeared;"
    )
    stmts.append("COMMIT;")
    return "\n".join(stmts)


def apply_snapshot_pg(
    db: Db, region_code: str, contract_month: str, deals: list[Deal], today: date, bootstrap: bool
) -> list[Event]:
    known = load_known(db, region_code, contract_month)
    d = diff_snapshot(known, deals, today, bootstrap)
    db.query(build_sql(region_code, contract_month, len(deals), d, today, bootstrap))
    return d.events


def should_bootstrap(db: Db, region_code: str, contract_month: str, today: date) -> bool:
    """처음 받는 칸이고, 그 시군구를 최근 3일(오늘 제외) 안에 받은 적이 없으면 bootstrap."""
    r = select(
        db,
        "SELECT "
        f"EXISTS (SELECT 1 FROM snapshot_runs WHERE region_code = {lit(region_code)} "
        f"AND contract_month = {lit(contract_month)}) AS cell_seen, "
        f"EXISTS (SELECT 1 FROM snapshot_runs WHERE region_code = {lit(region_code)} "
        f"AND run_date BETWEEN {lit(today)} - 3 AND {lit(today)} - 1) AS recent",
    )[0]
    return not r["cell_seen"] and not r["recent"]
