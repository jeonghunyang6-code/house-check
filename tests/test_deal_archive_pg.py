"""저장 구조 C 전 과정 (export → anchor → load → prune → roll). HC_TEST_PG_URL(빈 로컬 DB) 이 있을 때만 돈다."""
import os
import tempfile
from datetime import date
from pathlib import Path

import jobs.deal_archive as da
from collector.archive import LocalDirStore
from collector.db import PsqlDb, lit, select

ROOT = Path(__file__).parent.parent
URL = os.environ.get("HC_TEST_PG_URL")


def test_cutoff():
    assert (da.cutoff(date(2026, 10, 14)), da.cutoff(date(2026, 11, 1)), da.cutoff(date(2027, 1, 5))) == ("202410", "202411", "202501")


def test_archive_prune_roll_pg():
    if not URL:
        return
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, deal_anchor, deal_region_month CASCADE;")
    for m in ("0001_deals.sql", "0004_rls_deals.sql", "0010_metrics.sql", "0019_deal_anchor.sql"):
        db.query((ROOT / "db/migrations" / m).read_text())
    n = 0
    for d, p in (("2020-02-01", 50000), ("2021-11-01", 120000), ("2023-01-01", 90000), ("2024-12-01", 100000), ("2026-09-01", 130000)):
        n += 1
        db.query(f"INSERT INTO deals (deal_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, floor, price_10k, deal_type, last_seen_date) "
                 f"VALUES ('k{n}', 'A', 'x', '11680', {lit(d[:4]+d[5:7])}, {lit(date.fromisoformat(d))}, 84.9, 3, {p}, '중개', '2026-10-13')")
    db.query("INSERT INTO deal_events (deal_key, event, event_date) VALUES ('k1','registered','2020-02-05'), ('k5','registered','2026-09-05')")
    with tempfile.TemporaryDirectory() as t:
        st = LocalDirStore(t)
        ms = da.parse_months("202001-202410")
        assert da.run_export(db, st, ms, ["11680"]) == 0
        assert da.run_anchor(st, ms) == 0
        assert da.run_hist(st, ms) == 0
        from collector.archive import decode
        assert [r["deal_key"] for r in decode(st.get("deals_hist_11680.csv.gz"))] == ["k1", "k2", "k3"]
        assert da.run_load(db, st) == 0
        a = select(db, "select * from deal_anchor")
        assert len(a) == 1 and (a[0]["peak_10k"], a[0]["trough_10k"], a[0]["p20_10k"], a[0]["hist_high_10k"]) == (120000, 90000, 50000, 120000)
        assert da.run_prune(db, st, "202411") == 0
    assert [r["deal_key"] for r in select(db, "select deal_key from deals order by 1")] == ["k4", "k5"]
    assert select(db, "select deal_key from deal_events") == [{"deal_key": "k5"}]
    assert len(select(db, "select indexname from pg_indexes where tablename='deals'")) == 4
    assert select(db, "select relrowsecurity from pg_class where relname='deals'")[0]["relrowsecurity"] is True
    assert any(r["conname"] == "deal_events_deal_key_fkey" for r in select(db, "select conname from pg_constraint where conrelid='deal_events'::regclass"))
    # roll: 2026-11-05 → cutoff 202411 → 202410 이 빠져야 한다 (k4 는 202412 라 남음). 202410 거래 추가
    db.query("INSERT INTO deals (deal_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, floor, price_10k, deal_type, last_seen_date) VALUES "
             "('k6','A','x','11680','202410','2024-10-02',84.9,3,150000,'중개','2026-10-13'), ('k7','B','y','11680','202410','2024-10-03',59.9,3,70000,'중개','2026-10-13')")
    db.query("INSERT INTO deal_events (deal_key, event, event_date) VALUES ('k6','registered','2024-10-10')")
    with tempfile.TemporaryDirectory() as t:
        st = LocalDirStore(t)
        assert da.run_roll(db, st, ["11680"], date(2026, 11, 5)) == 0
        assert sorted(os.listdir(t)) == ["deals_202410.csv.gz", "deals_hist_11680.csv.gz"]
    a = {r["apt_seq"]: r for r in select(db, "select apt_seq, hist_high_10k, peak_10k from deal_anchor")}
    assert (a["A"]["hist_high_10k"], a["A"]["peak_10k"], a["B"]["hist_high_10k"]) == (150000, 120000, 70000)
    assert {r["region_code"] for r in select(db, "select region_code from deal_region_month where contract_month='202410'")} == {"11", "11680"}
    assert [r["deal_key"] for r in select(db, "select deal_key from deals order by 1")] == ["k4", "k5"]
    assert da.run_roll(db, LocalDirStore(tempfile.mkdtemp()), ["11680"], date(2026, 11, 5)) == 0   # 두 번째는 할 일 없음
