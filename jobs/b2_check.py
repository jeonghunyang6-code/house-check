"""B2 회복 패턴 계속 검증 (0060). 분기마다 complex_metrics 의 패턴을 b2_snapshot 에 저장하고,
저장한 지 12·24개월이 지난 스냅숏을 지금 기준 시세와 비교해 b2_validation 에 쌓는다. rone.yml 이 매주 부른다(할 일 없으면 바로 끝).

    python -m jobs.b2_check
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select

KST = ZoneInfo("Asia/Seoul")
HORIZONS = (12, 24)
WINDOW = 3     # 기간이 지난 뒤 이 개월 안에 한 번 평가한다(그 뒤에 처음 돌면 늦은 값이라 건너뜀)
# 2026-10-19 백테스트(tools/analysis/backtest_b2.py, 84㎡, 2026-08 까지): (판정 시점, 개월, 패턴, 단지 수, 초과 평균 %p, 더 오른 비율 %)
SEED = (
    ("2024-06-30", 26, "신고가 돌파", 23, -1.26, 48), ("2024-06-30", 26, "순조로운 회복", 58, -1.19, 38), ("2024-06-30", 26, "회복 지연", 1779, 0.65, 49),
    ("2024-12-31", 20, "신고가 돌파", 46, -1.96, 43), ("2024-12-31", 20, "순조로운 회복", 137, 1.58, 50), ("2024-12-31", 20, "회복 지연", 1385, 0.82, 49),
)


def snapshot(db: Db, today: date) -> int:
    q = f"{today.year}-{(today.month - 1) // 3 * 3 + 1:02d}-01"
    if select(db, f"SELECT count(*) AS n FROM b2_snapshot WHERE asof >= {lit(q)}::date")[0]["n"]:
        return 0
    db.query(f"""INSERT INTO b2_snapshot (asof, apt_seq, area_group, region_code, pattern, recovery, ref_10k)
SELECT {lit(today)}, m.apt_seq, m.area_group, c.region_code, m.pattern, m.recovery, m.ref_10k
FROM complex_metrics m JOIN complexes c USING (apt_seq) WHERE m.pattern IS NOT NULL AND m.ref_10k IS NOT NULL;""")
    n = select(db, f"SELECT count(*) AS n FROM b2_snapshot WHERE asof = {lit(today)}")[0]["n"]
    print(f"  B2 스냅숏 {today}: {n:,}개 단지·면적")
    return n


def evaluate(db: Db, today: date) -> int:
    done = 0
    for h in HORIZONS:
        due = select(db, f"""SELECT DISTINCT s.asof::text AS d FROM b2_snapshot s
WHERE s.asof + make_interval(months => {h}) <= {lit(today)}::date AND s.asof + make_interval(months => {h + WINDOW}) > {lit(today)}::date
  AND NOT EXISTS (SELECT 1 FROM b2_validation v WHERE v.asof = s.asof AND v.horizon_m = {h} AND v.source = 'snapshot')""")
        for r in due:
            db.query(f"""INSERT INTO b2_validation (asof, horizon_m, pattern, n, mean_excess, beat_pct, source, evaluated_at)
WITH x AS (
  SELECT s.region_code, s.pattern, m.ref_10k::numeric / s.ref_10k - 1 AS ret
  FROM b2_snapshot s JOIN complex_metrics m ON m.apt_seq = s.apt_seq AND m.area_group = s.area_group AND m.ref_10k IS NOT NULL
  WHERE s.asof = {lit(r['d'])}::date
), med AS (SELECT region_code, percentile_cont(0.5) WITHIN GROUP (ORDER BY ret)::numeric AS mr FROM x GROUP BY 1)
SELECT {lit(r['d'])}::date, {h}, x.pattern, count(*), round(avg(x.ret - med.mr) * 100, 2),
  round(avg((x.ret > med.mr)::int) * 100, 1), 'snapshot', {lit(today)}
FROM x JOIN med USING (region_code) GROUP BY x.pattern
ON CONFLICT DO NOTHING;""")
            done += 1
            print(f"  B2 검증 {r['d']} → {h}개월 뒤 평가")
    return done


def seed(db: Db, today: date) -> None:
    vals = ", ".join(f"({lit(d)}::date, {h}, {lit(p)}, {n}, {e}, {b}, 'backtest', {lit(today)})" for d, h, p, n, e, b in SEED)
    db.query("INSERT INTO b2_validation (asof, horizon_m, pattern, n, mean_excess, beat_pct, source, evaluated_at) VALUES "
             + vals + " ON CONFLICT DO NOTHING;")


def run(db: Db, today: date) -> int:
    seed(db, today)
    snapshot(db, today)
    evaluate(db, today)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), datetime.now(KST).date())
    except DbError as e:
        print(f"[b2_check] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
