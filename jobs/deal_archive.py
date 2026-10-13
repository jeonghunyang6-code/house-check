"""매매 원본 보관 (저장 구조 C, 2026-10-14). 무료 플랜 DB 500MB 를 넘어 읽기 전용이 돼서,
오래된 매매 원본을 GitHub Releases 의 월별 CSV.gz (`deals_YYYYMM.csv.gz`) 로 옮기고 DB 에는 최근 2년만 둔다.

    python -m jobs.deal_archive export --months 202001-202409 --archive gh   # DB → 파일 (DB 는 읽기만)

파일 하나 = 계약월 1개 × 수도권 전체 시군구. 올린 뒤 다시 내려받아 행 수를 DB 와 맞춰 본다.
DB 에서 지우는 단계는 따로(사용자 확인 뒤) 둔다. 종료 코드: 0 정상, 1 불일치·실패.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.archive import asset_name, decode, encode, open_store
from collector.db import Db, DbError, connect, lit, select
from collector.regions import select_regions
from jobs.daily import parse_months

KST = ZoneInfo("Asia/Seoul")
DEAL_COLUMNS = (
    "deal_key", "apt_seq", "apt_name", "region_code", "contract_month", "contract_date", "area_m2", "floor",
    "price_10k", "deal_type", "is_cancelled", "cancel_date", "rgst_date", "first_seen_date", "last_seen_date",
    "disappeared", "prev_high_10k",
)


def month_rows(db: Db, month: str, regions: list[str]) -> list[dict]:
    # ORDER BY 없이 읽는다(디스크가 꽉 찼을 때 정렬 임시 파일을 못 쓴다). 정렬은 여기서
    rows = select(db, f"SELECT {', '.join(DEAL_COLUMNS)} FROM deals WHERE contract_month = {lit(month)} "
                      f"AND region_code IN ({', '.join(lit(r) for r in regions)})")
    return sorted(rows, key=lambda r: (r["region_code"], r["deal_key"]))


def run_export(db: Db, store, months: list[str], regions: list[str]) -> int:
    bad = 0
    for m in months:
        t = time.time()
        rows = month_rows(db, m, regions)
        name = asset_name("deal", m)
        store.put(name, encode(rows, DEAL_COLUMNS))
        back = store.get(name)
        n_back = len(decode(back)) if back else -1
        ok = n_back == len(rows)
        bad += not ok
        print(f"  {name}: DB {len(rows):,}행 → 파일 {n_back:,}행 {'확인' if ok else '불일치'} ({time.time() - t:.0f}초)")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["export"])
    ap.add_argument("--months", required=True)
    ap.add_argument("--regions", default="sudogwon")
    ap.add_argument("--archive")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    print(f"[deal_archive] {a.step} {a.months} {datetime.now(KST):%Y-%m-%d %H:%M}")
    try:
        return run_export(connect(a.db), open_store(a.archive), parse_months(a.months), select_regions(a.regions))
    except DbError as e:
        print(f"[deal_archive] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
