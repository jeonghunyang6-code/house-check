"""Postgres 판 스냅샷 반영 통합 테스트. HC_TEST_PG_URL(빈 로컬 DB) 이 있을 때만 돈다.

    HC_TEST_PG_URL=postgresql://postgres@/postgres?host=/sock&port=55432 pytest tests/test_pg_store.py
"""
import os
from dataclasses import replace
from datetime import date
from pathlib import Path

from collector.db import PsqlDb, lit, select
from collector.pg_store import apply_snapshot_pg, should_bootstrap
from collector.snapshot import apply_snapshot, open_store
from collector.sources.molit import parse_trade_page

ROOT = Path(__file__).parent.parent
XML = (Path(__file__).parent / "fixtures" / "molit_trade_sample.xml").read_text(encoding="utf-8")
URL = os.environ.get("HC_TEST_PG_URL")


def _db():
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, snapshot_runs CASCADE;")
    for m in ("0001_deals.sql", "0005_snapshot_runs.sql"):
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
