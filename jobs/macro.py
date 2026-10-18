"""거시 월별 지표 적재 (collector/sources/kosis.py·ecos.py, 0012). rone weekly 뒤, market 앞에 돈다.

    python -m jobs.macro

시계열이 짧아(2000년~, 지표마다 1회 호출) 매번 전체를 받아 덮어쓴다. 발표 후 수정치와 계절조정 재추정도 그대로 반영된다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit
from collector.regions import REGIONS
from collector.sources import ecos, kosis
from collector.sources.molit import ApiError, QuotaExceeded

KST = ZoneInfo("Asia/Seoul")
START = "200001"
UNSOLD_START = "202001"


def upsert(db: Db, series: str, pts: list[tuple[str, float]], today) -> None:
    vals = ", ".join(f"({lit(series)}, {lit(p)}, {lit(v)}, {lit(today)})" for p, v in pts)
    db.query("INSERT INTO macro_monthly (series, period, value, fetched_at) VALUES " + vals +
             " ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value, fetched_at = EXCLUDED.fetched_at;")


def run(db: Db) -> int:
    today = datetime.now(KST).date()
    rc = 0
    for src in (kosis, ecos):
        for name in src.SERIES:
            try:
                pts = src.fetch(name, START, today.strftime("%Y%m"))
            except (ApiError, QuotaExceeded) as e:
                print(f"  {name}: 실패 {e}", file=sys.stderr)
                rc = 1
                continue
            if pts:
                upsert(db, name, pts, today)
            print(f"  {name}: {len(pts)}개 기간" + (f", 최신 {pts[-1][0]} = {pts[-1][1]}" if pts else ""))
    return run_unsold(db, today) or rc


def run_unsold(db: Db, today) -> int:
    """F3 시군구별 미분양 (0042). 2020년부터 전체를 덮어쓴다."""
    try:
        rows = kosis.fetch_unsold_sgg(UNSOLD_START, today.strftime("%Y%m"))
    except (ApiError, QuotaExceeded) as e:
        print(f"  시군구 미분양: 실패 {e}", file=sys.stderr)
        return 1
    if not rows:
        print("  시군구 미분양: 0건", file=sys.stderr)
        return 1
    codes = {(r["sido"], r["name"]): ",".join(kosis.sgg_codes(r["sido"], r["name"], REGIONS)) or None for r in rows}
    vals = [f"({lit(r['period'])}, {lit(r['sido'])}, {lit(r['name'])}, {lit(codes[(r['sido'], r['name'])])}, {r['unsold']}, {lit(r['unsold_done'])})"
            for r in rows]
    stmts = ["BEGIN;", f"DELETE FROM unsold_sgg WHERE period >= {lit(UNSOLD_START)};"]
    for i in range(0, len(vals), 1000):
        stmts.append("INSERT INTO unsold_sgg (period, sido, name, region_codes, unsold, unsold_done) VALUES " + ", ".join(vals[i:i + 1000]) + ";")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    miss = sorted({f"{s} {n}" for (s, n), c in codes.items() if c is None})
    last = max(r["period"] for r in rows)
    print(f"  시군구 미분양: {len(rows)}행, 최신 {last} {sum(r['unsold'] for r in rows if r['period'] == last):,}호"
          + (f", 코드 못 맞춤 {miss}" if miss else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--unsold-only", action="store_true", help="시군구 미분양만")
    a = ap.parse_args(argv)
    try:
        db = connect(a.db)
        rc = run_unsold(db, datetime.now(KST).date()) if a.unsold_only else run(db)
    except DbError as e:
        print(f"[macro] 실패: {e}", file=sys.stderr)
        return 1
    print(f"[macro] done rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
