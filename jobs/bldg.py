"""H5 건축물대장 수집 (collector/bldg.py → complex_bldg, 0054). 하루 호출 한도가 있어 매일 limit 만큼, 못 받은 단지부터.

    python -m jobs.bldg --limit 4000
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.bldg import fetch
from collector.db import Db, DbError, connect, lit, select
from collector.sources.molit import ApiError, QuotaExceeded

KST = ZoneInfo("Asia/Seoul")
MAX_YEAR = 2005        # 🔧 2027~28년에 20년+ (재건축 후보를 넉넉히)
FAIL_STREAK = 20
COLS = ("src", "plat_area", "vl_rat", "vl_rat_calc", "estm_area", "tot_area", "hhld", "main_bld", "land_per_hh")


def upsert_sql(rows: list[tuple[str, dict]], today: date) -> str:
    vals = ", ".join("(" + ", ".join([lit(s), *(lit(r.get(c)) for c in COLS), lit(today)]) + ")" for s, r in rows)
    return (f"INSERT INTO complex_bldg (apt_seq, {', '.join(COLS)}, fetched_at) VALUES {vals} ON CONFLICT (apt_seq) DO UPDATE SET "
            + ", ".join(f"{c} = EXCLUDED.{c}" for c in (*COLS, "fetched_at")) + ";")


def run(db: Db, limit: int, today: date, fetch=fetch) -> int:
    todo = select(db, f"""SELECT c.apt_seq, c.bjd_code, c.jibun FROM complexes c
WHERE c.build_year <= {MAX_YEAR} AND NOT EXISTS (SELECT 1 FROM complex_bldg b WHERE b.apt_seq = c.apt_seq)
ORDER BY c.build_year, c.apt_seq LIMIT {int(limit)}""")
    batch, done, streak, rc = [], 0, 0, 0
    for t in todo:
        try:
            r = fetch(t["bjd_code"], t["jibun"])
            streak = 0
        except QuotaExceeded as e:
            print(f"  호출 한도 초과로 중단: {e}", file=sys.stderr)
            rc = 2
            break
        except ApiError as e:
            streak += 1
            print(f"  {t['apt_seq']}: 실패 {e}", file=sys.stderr)
            if streak >= FAIL_STREAK:
                print(f"  실패가 {streak}번 연달아 중단", file=sys.stderr)
                rc = 2
                break
            continue
        batch.append((t["apt_seq"], r))
        done += 1
        if len(batch) >= 200:
            db.query(upsert_sql(batch, today))
            batch.clear()
            print(f"  {done}/{len(todo)}", flush=True)
    if batch:
        db.query(upsert_sql(batch, today))
    s = select(db, f"""SELECT count(*) AS n, count(*) FILTER (WHERE src <> 'none') AS found, count(*) FILTER (WHERE plat_area > 0) AS plat,
  (SELECT count(*) FROM complexes c WHERE c.build_year <= {MAX_YEAR} AND NOT EXISTS (SELECT 1 FROM complex_bldg b WHERE b.apt_seq = c.apt_seq)) AS left
FROM complex_bldg""")[0]
    print(f"  이번 {done}곳. 전체 {s['n']}곳 중 대장 찾음 {s['found']}·대지면적 있음 {s['plat']}, 남은 단지 {s['left']}곳")
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run(connect(a.db), a.limit, datetime.now(KST).date())
    except DbError as e:
        print(f"[bldg] 실패: {e}", file=sys.stderr)
        return 1
    print(f"[bldg] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
