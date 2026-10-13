"""급지 E1 계산 (collector/grade.py, 0017). 분기마다 한 번: 마지막 계산이 REFRESH_DAYS 안이면 건너뛴다.

    python -m jobs.grade            # 필요할 때만
    python -m jobs.grade --force    # 지금 다시 계산
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.grade import Complex, dong_grades

KST = ZoneInfo("Asia/Seoul")
REFRESH_DAYS = 85


def complexes(db: Db, today: date) -> list[Complex]:
    rows = select(db, f"""
WITH t AS (
  SELECT d.apt_seq, d.region_code, x.umd_name, x.apt_name, x.build_year, x.kapt_code, d.price_10k * 84.0 / d.area_m2 AS p84
  FROM deals d JOIN complexes x USING (apt_seq)
  WHERE NOT d.is_cancelled AND d.deal_type = '중개' AND d.area_m2 BETWEEN 40 AND 135
    AND d.contract_date > {lit(today)}::date - 365 AND x.umd_name IS NOT NULL AND x.build_year IS NOT NULL)
SELECT t.apt_seq, t.region_code, t.umd_name, max(t.apt_name) AS name, max(t.build_year) AS by,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY p84) AS p, count(*) AS n, max(k.households) AS hh
FROM t LEFT JOIN kapt_complexes k ON k.kapt_code = t.kapt_code
GROUP BY 1, 2, 3 HAVING count(*) >= 2""")
    return [Complex(r["region_code"], r["umd_name"], r["name"], int(r["by"]), float(r["p"]), int(r["n"]),
                    int(r["hh"]) if r["hh"] is not None else None) for r in rows]


def run(db: Db, today: date, force: bool = False) -> int | None:
    last = select(db, "SELECT max(asof)::text AS d FROM dong_grade")[0]["d"]
    if not force and last and (today - date.fromisoformat(last)).days < REFRESH_DAYS:
        print(f"  마지막 계산 {last}, {REFRESH_DAYS}일 안이라 건너뜀")
        return None
    out = dong_grades(complexes(db, today), today.year)
    cols = ("region_code", "umd_name", "grade", "value_10k", "q1_10k", "q3_10k", "n_complex", "n_deals", "old_share",
            "flag_rebuild", "flag_gap", "new_big_name", "new_big_10k")
    stmts = ["BEGIN;", f"DELETE FROM dong_grade WHERE asof = {lit(today)};"]
    for i in range(0, len(out), 300):
        vals = ", ".join("(" + lit(today) + ", " + ", ".join(lit(g[c]) for c in cols) + ")" for g in out[i:i + 300])
        stmts.append(f"INSERT INTO dong_grade (asof, {', '.join(cols)}) VALUES {vals};")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    return len(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    today = datetime.now(KST).date()
    try:
        n = run(connect(a.db), today, a.force)
    except DbError as e:
        print(f"[grade] 실패: {e}", file=sys.stderr)
        return 1
    if n is not None:
        print(f"  급지 {n}개 동 ({today})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
