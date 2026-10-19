"""C1 신고 지연 보정 거래량 (collector/volume.py, 0063). daily.yml 이 매일 수집 뒤 부른다.
당월·전월을 지역(서울·인천·경기·수도권)별로 추정해 volume_nowcast 에 남기고, 끝난 지 90일 지난 달은 actual 을 채운다.

    python -m jobs.volume
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

from collector import volume as V
from collector.db import Db, DbError, connect, lit, select
from jobs.daily import KST, default_months

LAG_DAYS = 28        # 최근 몇 일 동안 새로 보인 거래로 지연 분포를 재나
REGIONS = {"11": "서울", "28": "인천", "41": "경기"}
CHECK_AFTER = 90     # 계약 달이 끝나고 이만큼 지나면 거의 다 신고된 것으로 본다


def lags(db: Db, today: date) -> tuple[list[int], int]:
    rows = select(db, f"""SELECT first_seen_date - contract_date AS l, first_seen_date::text AS f FROM deals
WHERE first_seen_date > {lit(today)}::date - {LAG_DAYS} AND first_seen_date <= {lit(today)}::date
  AND contract_month IN (to_char(first_seen_date, 'YYYYMM'), to_char(first_seen_date - interval '1 month', 'YYYYMM'))""")
    return [r["l"] for r in rows], len({r["f"] for r in rows})


def weekday(db: Db) -> list[float]:
    rows = select(db, """SELECT extract(isodow FROM contract_date)::int - 1 AS w, count(*) AS n FROM deals
WHERE contract_date < date_trunc('month', current_date) - interval '3 months' GROUP BY 1""")
    return V.weekday_weights({r["w"]: r["n"] for r in rows})


def run(db: Db, today: date) -> int:
    ls, ndays = lags(db, today)
    if len(ls) < V.MIN_LAGS or ndays < V.MIN_DAYS:
        print(f"  C1: 지연 표본 {len(ls):,}건·{ndays}일 — 부족해서 건너뜀")
    else:
        wk = weekday(db)
        months = default_months(today)
        obs = select(db, f"""SELECT left(region_code, 2) AS r, contract_month AS m, count(*) FILTER (WHERE NOT is_cancelled) AS n
FROM deals WHERE contract_month IN ({', '.join(lit(m) for m in months)}) GROUP BY 1, 2""")
        cnt: dict[tuple[str, str], int] = {}
        for r in obs:
            if r["r"] in REGIONS:
                cnt[(r["r"], r["m"])] = r["n"]
                cnt[("capital", r["m"])] = cnt.get(("capital", r["m"]), 0) + r["n"]
        sb = {m: V.share_boot(m, today, ls, wk) for m in months}
        vals = []
        for (rg, m), n in sorted(cnt.items()):
            x = V.nowcast(n, sb[m])
            if not x:
                continue
            vals.append(f"({lit(today)}, {lit(rg)}, {lit(m)}, {n}, {x['share']:.3f}, {x['month_frac']:.3f}, {x['est']}, "
                        f"{lit(x['lo'])}, {lit(x['hi'])}, {lit(x['full'])}, {len(ls)})")
            print(f"  C1 {REGIONS.get(rg, '수도권')} {m}: 보임 {n:,} / 보인 비율 {x['share']:.0%} → 추정 {x['est']:,}"
                  f" ({x['lo']:,}~{x['hi']:,}), 한 달 전체 {x['full']:,}")
        if vals:
            db.query("INSERT INTO volume_nowcast (asof, region_code, contract_month, observed, share, month_frac, est, lo, hi, est_full, n_lags) VALUES "
                     + ", ".join(vals) + """ ON CONFLICT (asof, region_code, contract_month) DO UPDATE SET observed = EXCLUDED.observed,
share = EXCLUDED.share, month_frac = EXCLUDED.month_frac, est = EXCLUDED.est, lo = EXCLUDED.lo, hi = EXCLUDED.hi,
est_full = EXCLUDED.est_full, n_lags = EXCLUDED.n_lags;""")
    # 검증: 끝난 지 90일 지난 달의 지금 건수
    db.query(f"""WITH due AS (
  SELECT DISTINCT contract_month FROM volume_nowcast
  WHERE actual IS NULL AND (to_date(contract_month, 'YYYYMM') + interval '1 month' + make_interval(days => {CHECK_AFTER}))::date <= {lit(today)}::date
), c AS (
  SELECT left(region_code, 2) AS r, contract_month, count(*) FILTER (WHERE NOT is_cancelled) AS n
  FROM deals WHERE contract_month IN (SELECT contract_month FROM due) GROUP BY 1, 2
), c2 AS (
  SELECT r, contract_month, n FROM c WHERE r IN ('11', '28', '41')
  UNION ALL SELECT 'capital', contract_month, sum(n) FROM c WHERE r IN ('11', '28', '41') GROUP BY contract_month
)
UPDATE volume_nowcast v SET actual = c2.n FROM c2 WHERE v.actual IS NULL AND v.region_code = c2.r AND v.contract_month = c2.contract_month;""")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), datetime.now(KST).date())
    except DbError as e:
        print(f"[volume] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
