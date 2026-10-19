"""R9 인지도(검색량) 수집 (collector/searchtrend.py → complex_search, 0057). NAVER API HUB 검색어 트렌드, 한 번에 limit 개 요청까지.
대상: 🔧 300세대 이상이고 최근 1년 거래가 있는 단지, 큰 단지부터. 이번 달에 받은 단지는 건너뛴다.

    python -m jobs.searchtrend --limit 900
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.searchtrend import PER_CALL, body, call, index, keyword
from collector.sources.molit import ApiError, QuotaExceeded

KST = ZoneInfo("Asia/Seoul")
MONTHS = 12
MIN_HH = 300


def window(today: date) -> tuple[str, str]:
    """지난달까지 MONTHS 개월 (YYYY-MM-01 ~ 지난달 말일)."""
    y, m = today.year, today.month - 1
    if m == 0:
        y, m = y - 1, 12
    end = date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1
    sy, sm = y, m - MONTHS + 1
    while sm < 1:
        sy, sm = sy - 1, sm + 12
    return f"{sy}-{sm:02d}-01", date.fromordinal(end).isoformat()


def run(db: Db, limit: int, today: date, call=call) -> int:
    cx = select(db, f"""SELECT c.apt_seq, c.apt_name, c.umd_name FROM complexes c JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
WHERE k.households >= {MIN_HH} AND EXISTS (SELECT 1 FROM deals d WHERE d.apt_seq = c.apt_seq AND d.contract_date > {lit(today)}::date - 365)
  AND NOT EXISTS (SELECT 1 FROM complex_search s WHERE s.apt_seq = c.apt_seq AND date_trunc('month', s.fetched_at) = date_trunc('month', {lit(today)}::date))
ORDER BY k.households DESC""")
    todo = [(c["apt_seq"], k) for c in cx if (k := keyword(c["apt_name"], c["umd_name"]))]
    start, end = window(today)
    done, rc = 0, 0
    for i in range(0, min(len(todo), limit * PER_CALL), PER_CALL):
        chunk = todo[i:i + PER_CALL]
        try:
            out = index(call(body(start, end, [(s, [k]) for s, k in chunk])), MONTHS)
        except QuotaExceeded as e:
            print(f"  호출 한도로 중단: {e}", file=sys.stderr)
            rc = 2
            break
        except ApiError as e:
            print(f"  실패로 중단: {e}", file=sys.stderr)   # 401(키 오류)·403 이면 더 부르지 않는다
            rc = 1
            break
        vals = [f"({lit(s)}, {lit(k)}, {MONTHS}, {out.get(s, {}).get('n', 0)}, {lit(out.get(s, {}).get('avg'))}, "
                f"{lit(out.get(s, {}).get('idx'))}, {lit(today)})" for s, k in chunk]
        db.query("INSERT INTO complex_search (apt_seq, keyword, months, n_months, avg_ratio, idx, fetched_at) VALUES " + ", ".join(vals)
                 + " ON CONFLICT (apt_seq) DO UPDATE SET keyword = EXCLUDED.keyword, months = EXCLUDED.months, n_months = EXCLUDED.n_months, "
                 "avg_ratio = EXCLUDED.avg_ratio, idx = EXCLUDED.idx, fetched_at = EXCLUDED.fetched_at;")
        done += len(chunk)
        time.sleep(0.2)
    print(f"  대상 {len(todo)}곳(이름이 짧아 뺀 곳 {len(cx) - len(todo)}) 중 이번 {done}곳, 기간 {start}~{end}")
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2000, help="요청 수 (API HUB 월 50,000)")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.limit, datetime.now(KST).date())
    except DbError as e:
        print(f"[searchtrend] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
