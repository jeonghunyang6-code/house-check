"""Postgres 판 스냅샷 반영 통합 테스트. HC_TEST_PG_URL(빈 로컬 DB) 이 있을 때만 돈다.

    HC_TEST_PG_URL=postgresql://postgres@/postgres?host=/sock&port=55432 pytest tests/test_pg_store.py
"""
import os
from dataclasses import replace
from datetime import date
from pathlib import Path

from collector.db import PsqlDb, lit, select
from collector.pg_store import RENT, apply_snapshot_pg, done_cells, should_bootstrap
from collector.snapshot import apply_snapshot, open_store
from collector.sources.molit import parse_rent_page, parse_trade_page

ROOT = Path(__file__).parent.parent
XML = (Path(__file__).parent / "fixtures" / "molit_trade_sample.xml").read_text(encoding="utf-8")
RENT_XML = (Path(__file__).parent / "fixtures" / "molit_rent_sample.xml").read_text(encoding="utf-8")
URL = os.environ.get("HC_TEST_PG_URL")


def _db():
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, rent_events, rents, snapshot_runs CASCADE;")
    for m in ("0001_deals.sql", "0005_snapshot_runs.sql", "0006_rents.sql"):
        db.query((ROOT / "db" / "migrations" / m).read_text(encoding="utf-8"))
    return db


def test_lit_quotes_and_types():
    assert lit("O'Neil") == "'O''Neil'"
    assert lit(None) == "NULL" and lit(True) == "TRUE" and lit(3) == "3"
    assert lit(date(2026, 1, 2)) == "'2026-01-02'::date"


def test_pg_matches_sqlite_events_and_state():
    if not URL:
        return
    deals, _ = parse_trade_page(XML)
    base = [d for d in deals if not d.is_cancelled]
    victim = base[0]
    steps = [
        (base[:2], date(2026, 10, 11), True),
        (base, date(2026, 10, 12), False),
        ([replace(victim, is_cancelled=True, cancel_date=date(2026, 10, 12))] + base[1:], date(2026, 10, 13), False),
        (base[1:], date(2026, 10, 14), False),
        (base[1:], date(2026, 10, 15), False),
        (deals, date(2026, 10, 16), False),
    ]
    db, con = _db(), open_store()
    for snap, day, boot in steps:
        e_pg = apply_snapshot_pg(db, "11680", "202608", snap, day, boot)
        e_lite = apply_snapshot(con, "11680", "202608", snap, day, boot)
        assert e_pg == e_lite, day
    pg = select(db, "SELECT deal_key, is_cancelled, disappeared, first_seen_date::text AS f, last_seen_date::text AS l "
                    "FROM deals ORDER BY deal_key")
    lite = con.execute("SELECT deal_key, is_cancelled, disappeared, first_seen_date, last_seen_date FROM deals "
                       "ORDER BY deal_key").fetchall()
    assert [(r["deal_key"], r["is_cancelled"], r["disappeared"], r["f"], r["l"]) for r in pg] == \
           [(k, bool(c), bool(d), f, l) for k, c, d, f, l in lite]
    n_ev = select(db, "SELECT count(*) AS n FROM deal_events")[0]["n"]
    assert n_ev == con.execute("SELECT count(*) FROM deal_events").fetchone()[0]
    runs = select(db, "SELECT run_date::text AS d, n_deals, bootstrap FROM snapshot_runs ORDER BY run_date")
    assert [r["d"] for r in runs] == [s[1].isoformat() for s in steps] and runs[0]["bootstrap"] is True


def test_bootstrap_rule():
    if not URL:
        return
    db = _db()
    deals, _ = parse_trade_page(XML)
    assert should_bootstrap(db, "11680", "202609", date(2026, 10, 11))          # 처음
    apply_snapshot_pg(db, "11680", "202609", deals, date(2026, 10, 11), True)
    assert not should_bootstrap(db, "11680", "202609", date(2026, 10, 12))      # 이미 받은 칸
    assert not should_bootstrap(db, "11680", "202610", date(2026, 10, 12))      # 새 칸이지만 어제 받음 → 정상
    assert should_bootstrap(db, "11680", "202610", date(2026, 10, 20))          # 오래 끊겼다 재개 → bootstrap
    assert should_bootstrap(db, "11710", "202609", date(2026, 10, 12))          # 다른 시군구 처음
    # 같은 시군구의 한 달만 실패해 빠진 경우: 다음 날 그 칸은 놓친 칸이므로 bootstrap (신규 등록으로 몰아 찍지 않는다)
    apply_snapshot_pg(db, "11680", "202610", [], date(2026, 10, 12), False)
    assert should_bootstrap(db, "11680", "202608", date(2026, 10, 13))
    assert not should_bootstrap(db, "11680", "202611", date(2026, 10, 13))      # 마지막 달보다 새 달 + 어제 수집 → 정상


def test_rent_snapshot_and_kind_separation():
    if not URL:
        return
    db = _db()
    rents, _ = parse_rent_page(RENT_XML)
    assert apply_snapshot_pg(db, "11680", "202609", rents[:3], date(2026, 10, 11), True, kind=RENT) == []
    ev = apply_snapshot_pg(db, "11680", "202609", rents[1:], date(2026, 10, 12), False, kind=RENT)
    assert sorted(e.event for e in ev) == ["disappeared", "registered", "registered"]
    row = select(db, "SELECT contract_type, used_renewal_right, term_start::text AS ts, pre_deposit_10k "
                     "FROM rents WHERE used_renewal_right")[0]
    assert row["contract_type"] == "갱신" and row["ts"] and row["pre_deposit_10k"]
    assert select(db, "SELECT count(*) AS n FROM rents WHERE contract_type IS NULL")[0]["n"] == 1
    # 매매와 전월세의 수집 기록은 서로 섞이지 않는다
    assert should_bootstrap(db, "11680", "202609", date(2026, 10, 12))
    assert done_cells(db, RENT, ["11680", "11710"], ["202609", "202608"]) == {("11680", "202609")}
