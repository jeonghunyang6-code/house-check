"""E8 상급지까지 거리 (collector/locality.py → complex_e8, 0052). rone.yml 이 매주 grade 뒤에 돌린다.

    python -m jobs.locality
"""

from __future__ import annotations

import argparse
import sys

from collector.db import Db, DbError, connect, lit, select
from collector.locality import centroids, e8_rows

COLS = ("apt_seq", "grade", "up_rc", "up_dong", "up_grade", "up_m", "top_rc", "top_dong", "top_m")


def run(db: Db) -> int:
    asof = select(db, "SELECT max(asof)::text AS d FROM dong_grade")[0]["d"]
    if not asof:
        print("  급지 없음", file=sys.stderr)
        return 1
    grades = {(r["region_code"], r["umd_name"]): int(r["grade"])
              for r in select(db, f"SELECT region_code, umd_name, grade FROM dong_grade WHERE asof = {lit(asof)}")}
    cx = select(db, "SELECT apt_seq, region_code, umd_name, lat, lng FROM complexes")
    rows = e8_rows(cx, grades, centroids(cx))
    stmts = ["BEGIN;", "DELETE FROM complex_e8;"]
    for i in range(0, len(rows), 1000):
        stmts.append(f"INSERT INTO complex_e8 ({', '.join(COLS)}, grade_asof) VALUES "
                     + ", ".join("(" + ", ".join(lit(r[c]) for c in COLS) + f", {lit(asof)})" for r in rows[i:i + 1000]) + ";")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    up = sorted(r["up_m"] for r in rows if r["up_m"] is not None)
    tp = sorted(r["top_m"] for r in rows if r["top_m"] is not None)
    print(f"  단지 {len(rows)}곳 (급지 {asof}), 위 급지 거리 중앙값 {up[len(up) // 2] if up else '-'}m, "
          f"1~2급지 거리 중앙값 {tp[len(tp) // 2] if tp else '-'}m")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db))
    except DbError as e:
        print(f"[locality] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
