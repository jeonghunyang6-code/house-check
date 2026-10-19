"""jobs/b2_check.py — HC_TEST_PG_URL(빈 로컬 DB)이 있을 때만."""
import os
from datetime import date
from pathlib import Path

from collector.db import PsqlDb, select
from jobs.b2_check import evaluate, run, snapshot

ROOT = Path(__file__).parent.parent
URL = os.environ.get("HC_TEST_PG_URL")


def test_b2_snapshot_and_evaluate():
    if not URL:
        return
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS b2_snapshot, b2_validation, complex_metrics, complexes CASCADE;")
    db.query("CREATE TABLE complexes (apt_seq TEXT PRIMARY KEY, region_code TEXT);"
             "CREATE TABLE complex_metrics (apt_seq TEXT, area_group INT, ref_10k INT, pattern TEXT, recovery NUMERIC(6,3));")
    db.query((ROOT / "db" / "migrations" / "0060_b2_check.sql").read_text(encoding="utf-8"))
    db.query("INSERT INTO complexes VALUES ('A','11680'),('B','11680'),('C','11680'),('D','11680');"
             "INSERT INTO complex_metrics VALUES ('A',84,100000,'회복 지연',0.3),('B',84,100000,'회복 지연',0.2),"
             "('C',84,100000,'순조로운 회복',0.7),('D',84,100000,'신고가 돌파',1.1);")
    run(db, date(2026, 10, 19))
    assert select(db, "SELECT count(*) AS n FROM b2_snapshot")[0]["n"] == 4
    assert select(db, "SELECT count(*) AS n FROM b2_validation WHERE source = 'backtest'")[0]["n"] == 6
    assert snapshot(db, date(2026, 11, 30)) == 0                     # 같은 분기엔 다시 안 찍는다
    # 1년 뒤: A +20%, B +10%, C +5%, D +15% → 구 중앙값 +12.5%. 회복 지연 평균 +2.5%p·더 오른 비율 50%
    db.query("UPDATE complex_metrics SET ref_10k = CASE apt_seq WHEN 'A' THEN 120000 WHEN 'B' THEN 110000 WHEN 'C' THEN 105000 ELSE 115000 END;")
    assert evaluate(db, date(2027, 9, 1)) == 0                       # 아직 12개월 전
    assert evaluate(db, date(2027, 10, 25)) == 1
    v = {r["pattern"]: r for r in select(db, "SELECT pattern, n, mean_excess, beat_pct FROM b2_validation WHERE source = 'snapshot'")}
    assert (v["회복 지연"]["n"], float(v["회복 지연"]["mean_excess"]), float(v["회복 지연"]["beat_pct"])) == (2, 2.5, 50.0)
    assert float(v["순조로운 회복"]["mean_excess"]) == -7.5 and float(v["신고가 돌파"]["beat_pct"]) == 100.0
    assert evaluate(db, date(2027, 11, 1)) == 0                      # 한 번만
