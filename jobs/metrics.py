"""단지 지표 계산 (sql/metrics.sql, 0010). 매일 매매 수집 뒤 돈다. 계산은 DB 안에서 한다.

    python -m jobs.metrics                # 오늘(KST) 기준, 최근 120일 계약분의 전고점 갱신
    python -m jobs.metrics --prev-days 4000   # 처음 한 번: 모든 거래의 전고점
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from collector.db import DbError, connect, lit, select
from jobs.daily import default_months

KST = ZoneInfo("Asia/Seoul")
SQL = Path(__file__).resolve().parents[1] / "sql" / "metrics.sql"


def render(today: date, prev_days: int) -> str:
    cur, prev = default_months(today)
    return (SQL.read_text(encoding="utf-8")
            .replace("{TODAY}", lit(today)).replace("{PREV_DAYS}", str(int(prev_days)))
            .replace("{CUR_M}", lit(cur)).replace("{PREV_M}", lit(prev)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev-days", type=int, default=120, help="전고점을 다시 계산할 최근 계약 기간(일)")
    ap.add_argument("--today", help="기준일 YYYY-MM-DD (기본: KST 오늘)")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else datetime.now(KST).date()
    db = connect(a.db)
    t0 = time.monotonic()
    try:
        db.query(render(today, a.prev_days))
        r = select(db, "SELECT count(*) AS n, count(ref_10k) AS ref, count(pattern) AS pat, count(jeonse_ratio) AS jr FROM complex_metrics")[0]
    except DbError as e:
        print(f"[metrics] 실패: {e}", file=sys.stderr)
        return 1
    print(f"[metrics] {today} 단지·면적 {r['n']}개, 기준 시세 {r['ref']}개, 회복 패턴 {r['pat']}개, 전세가율 {r['jr']}개 "
          f"({time.monotonic() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
