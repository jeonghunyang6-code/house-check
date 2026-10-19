"""H5 건축물대장 수집 (collector/bldg.py → complex_bldg, 0054). 하루 호출 한도가 있어 매일 limit 만큼, 못 받은 단지부터.

    python -m jobs.bldg --limit 4000
    python -m jobs.bldg --atch --limit 3000      # 부속 지번(여러 필지 단지) → complex_land_lot (0061)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.bldg import fetch, fetch_atch
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


def run_atch(db: Db, limit: int, today: date, fetch_atch=fetch_atch) -> int:
    """부속 지번 수집. 대장 대지면적이 없는(VWorld 로 채우는) 단지부터."""
    todo = select(db, f"""SELECT c.apt_seq, c.bjd_code, c.jibun FROM complexes c LEFT JOIN complex_bldg b USING (apt_seq)
WHERE c.build_year <= {MAX_YEAR} AND NOT EXISTS (SELECT 1 FROM complex_atch_done a WHERE a.apt_seq = c.apt_seq)
ORDER BY (coalesce(b.plat_area, 0) > 0), c.build_year, c.apt_seq LIMIT {int(limit)}""")
    done, streak, rc, lots, batch = 0, 0, 0, 0, []

    def flush():
        if batch:
            db.query("BEGIN;\n" + "\n".join(batch) + "\nCOMMIT;")
            batch.clear()
    for t in todo:
        try:
            ps = fetch_atch(t["bjd_code"], t["jibun"])
            streak = 0
        except QuotaExceeded as e:
            print(f"  호출 한도 초과로 중단: {e}", file=sys.stderr)
            rc = 2
            break
        except ApiError as e:
            streak += 1
            print(f"  {t['apt_seq']}: 실패 {e}", file=sys.stderr)
            if streak >= FAIL_STREAK:
                rc = 2
                break
            continue
        if ps:
            batch.append("INSERT INTO complex_land_lot (apt_seq, pnu) VALUES " + ", ".join(f"({lit(t['apt_seq'])}, {lit(p)})" for p in sorted(ps))
                         + " ON CONFLICT DO NOTHING;")
            lots += len(ps)
        batch.append(f"INSERT INTO complex_atch_done (apt_seq, n_lots, fetched_at) VALUES ({lit(t['apt_seq'])}, {lit(None if ps is None else len(ps))}, {lit(today)}) "
                     "ON CONFLICT (apt_seq) DO UPDATE SET n_lots = EXCLUDED.n_lots, fetched_at = EXCLUDED.fetched_at;")
        done += 1
        if len(batch) >= 300:
            flush()
            print(f"  부속 지번 {done}/{len(todo)}", flush=True)
    flush()
    s = select(db, "SELECT count(*) AS n, count(*) FILTER (WHERE n_lots > 0) AS multi FROM complex_atch_done")[0]
    print(f"  부속 지번: 이번 {done}곳(필지 {lots}개). 전체 {s['n']}곳 중 부속 지번 있음 {s['multi']}곳")
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--atch", action="store_true", help="부속 지번만")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db, today = connect(a.db), datetime.now(KST).date()
        rc = run_atch(db, a.limit, today) if a.atch else run(db, a.limit, today)
    except DbError as e:
        print(f"[bldg] 실패: {e}", file=sys.stderr)
        return 1
    print(f"[bldg] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
