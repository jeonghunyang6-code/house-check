"""B5 ② 하위 급지 신고가 비중의 과거 월별 시계열 (0018 b5_history). 경고선 백테스트용, 수동 실행.

    python -m jobs.b5_history prev --regions sudogwon   # deals.prev_high_10k 를 2020년부터 다시 계산 (시군구별)
    python -m jobs.b5_history agg                       # 월별 집계

sql/metrics.sql 은 최근 120일 거래의 전고점만 매일 다시 계산한다. 그 이전 거래는 이 작업이 채운다.
과거에도 지금(최신 asof) 급지를 그대로 쓴다: 2021년 하위 급지 = 지금 기준 하위 급지인 동.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.regions import select_regions

KST = ZoneInfo("Asia/Seoul")
FROM = "2020-01-01"
RECENT_DAYS = 120   # 이보다 최근 거래는 jobs.metrics 가 매일 계산한다


def run_prev(db: Db, regions: list[str]) -> int:
    for i, rc in enumerate(regions, 1):
        t = time.time()
        db.query(f"""UPDATE deals d SET prev_high_10k = (
  SELECT max(p.price_10k) FROM deals p
  WHERE p.apt_seq = d.apt_seq AND p.area_group = d.area_group AND p.contract_date < d.contract_date
    AND NOT p.is_cancelled AND p.deal_type = '중개')
WHERE d.region_code = {lit(rc)} AND d.contract_date >= DATE {lit(FROM)} AND d.contract_date < current_date - {RECENT_DAYS};""")
        print(f"  [{i}/{len(regions)}] {rc} 전고점 {time.time() - t:.0f}초")
    return 0


def run_agg(db: Db) -> int:
    asof = select(db, "SELECT max(asof)::text AS d FROM dong_grade")[0]["d"]
    if not asof:
        print("  dong_grade 가 비어 있음 (jobs.grade 먼저)", file=sys.stderr)
        return 1
    db.query(f"""BEGIN;
DELETE FROM b5_history;
INSERT INTO b5_history
WITH g AS (SELECT region_code, umd_name, grade FROM dong_grade WHERE asof = DATE {lit(asof)}),
r AS (SELECT d.contract_month AS m, d.price_10k > d.prev_high_10k AS hi, g.grade,
        g.grade >= 6 AND x.build_year <= left(d.contract_month, 4)::int - 20 AND coalesce(k.households, 0) < 300 AS lip
  FROM deals d JOIN complexes x USING (apt_seq) JOIN g ON g.region_code = d.region_code AND g.umd_name = x.umd_name
  LEFT JOIN kapt_complexes k ON k.kapt_code = x.kapt_code
  WHERE NOT d.is_cancelled AND d.deal_type = '중개' AND d.prev_high_10k IS NOT NULL AND d.contract_date >= DATE '2021-01-01')
SELECT m, count(*) FILTER (WHERE grade >= 6), count(*) FILTER (WHERE grade >= 6 AND hi),
  count(*) FILTER (WHERE grade <= 3), count(*) FILTER (WHERE grade <= 3 AND hi),
  count(*) FILTER (WHERE lip), count(*) FILTER (WHERE lip AND hi), DATE {lit(asof)}
FROM r GROUP BY m;
COMMIT;""")
    for r in select(db, "SELECT month, n_low, h_low, n_top, h_top, n_lip, h_lip FROM b5_history ORDER BY month"):
        lo = r["h_low"] * 100 / r["n_low"] if r["n_low"] else 0
        tp = r["h_top"] * 100 / r["n_top"] if r["n_top"] else 0
        print(f"  {r['month']} 하위 {lo:5.1f}% ({r['n_low']:>6,}) 상위 {tp:5.1f}% ({r['n_top']:>5,}) 비 {lo / tp if tp else 0:.2f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prev", "agg"])
    ap.add_argument("--regions", default="sudogwon")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    print(f"[b5_history] {a.step} {datetime.now(KST):%Y-%m-%d %H:%M}")
    try:
        db = connect(a.db)
        return run_prev(db, select_regions(a.regions)) if a.step == "prev" else run_agg(db)
    except DbError as e:
        print(f"[b5_history] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
