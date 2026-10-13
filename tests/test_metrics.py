"""sql/metrics.sql 통합 테스트. HC_TEST_PG_URL(빈 로컬 DB) 이 있을 때만 돈다."""
import os
from datetime import date
from pathlib import Path

from collector.db import PsqlDb, lit, select
from jobs.metrics import render

ROOT = Path(__file__).parent.parent
URL = os.environ.get("HC_TEST_PG_URL")
TODAY = date(2026, 10, 12)


def _db():
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, rent_events, rents, snapshot_runs, rent_monthly, archive_cells, complex_metrics, "
             "macro_monthly, deal_anchor, deal_region_month, region_phase, market_signals, rone_weekly, rone_regions CASCADE;")
    for m in ("0001_deals.sql", "0005_snapshot_runs.sql", "0006_rents.sql", "0007_rent_archive.sql", "0010_metrics.sql",
              "0009_rone_weekly.sql", "0011_market.sql", "0012_macro.sql", "0013_macro_annual.sql", "0014_complex_phase.sql", "0015_quadrant_strength.sql",
              "0016_reverse_real.sql", "0019_deal_anchor.sql"):
        db.query((ROOT / "db" / "migrations" / m).read_text(encoding="utf-8"))
    return db


def _deal(db, seq, d, price, dtype="중개", cancelled=False, n=[0]):
    n[0] += 1
    db.query("INSERT INTO deals (deal_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, floor, "
             "price_10k, deal_type, is_cancelled, last_seen_date) VALUES "
             f"({lit(f'k{n[0]}')}, {lit(seq)}, 'x', '11680', {lit(d.replace('-', '')[:6])}, {lit(date.fromisoformat(d))}, 84.9, 5, "
             f"{price}, {lit(dtype)}, {lit(cancelled)}, {lit(TODAY)});")


def test_metrics_end_to_end():
    if not URL:
        return
    db = _db()
    # A: 2021 전고점 15억, 2023 저점 10억, 최근 60일 16·17·18억 → 기준 17억, 신고가 돌파
    for d in ("2021-06-05", "2021-06-20", "2021-07-10"):
        _deal(db, "A", d, 150000)
    _deal(db, "A", "2023-01-15", 100000)
    _deal(db, "A", "2026-09-01", 160000); _deal(db, "A", "2026-09-10", 170000); _deal(db, "A", "2026-10-01", 180000)
    _deal(db, "A", "2026-10-02", 999999, dtype="직거래")             # 직거래는 무시
    _deal(db, "A", "2026-10-03", 990000, cancelled=True)            # 해제도 무시
    db.query("INSERT INTO rent_monthly VALUES ('A', 84, '202610', '11680', 'x', 3, 81000, 2, 80000, 1, 0, NULL, NULL, 0, 0);")
    # B: 최근 거래 2건뿐 → 기준 시세 없음
    _deal(db, "B", "2026-10-01", 50000); _deal(db, "B", "2026-10-05", 51000)
    # C: 최근 60·90일엔 없고 100~180일 전 3건 → 180일 창, 신뢰도 낮음. 전고점 20억, 저점 10억, 현재 14억 → 회복 40% 지연
    _deal(db, "C", "2021-09-01", 200000); _deal(db, "C", "2023-03-01", 100000)
    for d in ("2026-05-01", "2026-05-10", "2026-06-01"):
        _deal(db, "C", d, 140000)

    db.query(render(TODAY, 4000))
    m = {r["apt_seq"]: r for r in select(db, "SELECT * FROM complex_metrics")}
    a, b, c = m["A"], m["B"], m["C"]
    assert (a["ref_10k"], a["ref_n"], a["ref_days"], a["confidence"]) == (170000, 3, 60, "높음")
    assert (a["peak_10k"], a["peak_month"], a["trough_10k"], a["pattern"]) == (150000, "202106", 100000, "신고가 돌파")
    assert (a["jeonse_10k"], a["jeonse_src"], float(a["jeonse_ratio"])) == (80000, "신규", 47.1)
    assert (float(a["band_lo"]), float(a["band_hi"])) == (42.0, 56.0)       # 17억: 50→30, 60→50 구간 40% 지점
    assert a["high_10k"] == 180000 and a["n_365"] == 3
    assert b["ref_10k"] is None and b["pattern"] is None and b["jeonse_ratio"] is None
    assert (c["ref_10k"], c["ref_days"], c["confidence"], c["pattern"], float(c["recovery"])) == (140000, 180, "낮음", "회복 지연", 0.4)
    assert c["no_rebound"] is False
    # 전고점: 18억 거래 직전 최고가는 17억 (직거래 999,999 와 해제 990,000 은 제외)
    ph = {r["price_10k"]: r["prev_high_10k"] for r in select(db, "SELECT price_10k, prev_high_10k FROM deals WHERE apt_seq = 'A'")}
    assert ph[180000] == 170000 and ph[160000] == 150000 and ph[150000] in (None, 150000)


def test_metrics_with_deal_anchor():
    """저장 구조 C: 2년 전 거래는 DB 에 없고 deal_anchor 에 고정값만 있다."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO deal_anchor VALUES ('D', 84, 200000, '2021-08-01', 190000, '202108', 120000, '202212', 90000);")
    _deal(db, "D", "2026-09-01", 150000); _deal(db, "D", "2026-09-10", 160000); _deal(db, "D", "2026-10-01", 170000)
    db.query(render(TODAY, 4000))
    d = select(db, "SELECT * FROM complex_metrics WHERE apt_seq = 'D'")[0]
    assert (d["ref_10k"], d["peak_10k"], d["peak_month"], d["trough_10k"], d["trough_month"]) == (160000, 190000, "202108", 120000, "202212")
    assert d["pattern"] == "회복 지연" and float(d["recovery"]) == 0.571
    assert d["high_10k"] == 200000 and str(d["high_date"]) == "2021-08-01" and d["base2020_10k"] == 90000
    prev = {r["price_10k"]: r["prev_high_10k"] for r in select(db, "SELECT price_10k, prev_high_10k FROM deals WHERE apt_seq = 'D'")}
    assert prev == {150000: 200000, 160000: 200000, 170000: 200000}   # 보관 구간 최고가가 전고점
