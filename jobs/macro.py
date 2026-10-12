"""거시 월별 지표 적재 (collector/sources/kosis.py, 0012). rone weekly 뒤, market 앞에 돈다.

    python -m jobs.macro

시계열이 짧아(2000년~, 1회 호출) 매번 전체를 받아 덮어쓴다. 발표 후 수정치와 계절조정 재추정도 그대로 반영된다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit
from collector.sources import kosis
from collector.sources.molit import ApiError, QuotaExceeded

KST = ZoneInfo("Asia/Seoul")
START = "200001"


def upsert(db: Db, series: str, pts: list[tuple[str, float]], today) -> None:
    vals = ", ".join(f"({lit(series)}, {lit(p)}, {lit(v)}, {lit(today)})" for p, v in pts)
    db.query("INSERT INTO macro_monthly (series, period, value, fetched_at) VALUES " + vals +
             " ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value, fetched_at = EXCLUDED.fetched_at;")


def run(db: Db) -> int:
    today = datetime.now(KST).date()
    rc = 0
    for name in kosis.SERIES:
        try:
            pts = kosis.fetch(name, START, today.strftime("%Y%m"))
        except (ApiError, QuotaExceeded) as e:
            print(f"  {name}: 실패 {e}", file=sys.stderr)
            rc = 1
            continue
        if pts:
            upsert(db, name, pts, today)
        print(f"  {name}: {len(pts)}개월" + (f", 최신 {pts[-1][0]} = {pts[-1][1]}" if pts else ""))
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        rc = run(connect(a.db))
    except DbError as e:
        print(f"[macro] 실패: {e}", file=sys.stderr)
        return 1
    print(f"[macro] done rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
