"""B5 ② 하위 급지 신고가 비중의 과거 월별 시계열 (0018 b5_history, collector/b5.py). 경고선 백테스트용, 수동 실행.

    python -m jobs.b5_history --archive gh

2024-09 이전 거래는 보관 파일(deals_YYYYMM.csv.gz), 그 뒤는 DB 에서 읽어 파이썬으로 전고점을 계산한다.
DB 에는 b5_history(월 80행 안팎)만 쓴다. (2026-10-14 전 버전은 deals.prev_high_10k 를 대량 UPDATE 하다
Supabase 무료 플랜이 읽기 전용이 됐다 — 그 방식은 버렸다)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.archive import asset_name, decode, open_store
from collector.b5 import monthly
from collector.db import Db, DbError, connect, lit, select
from jobs.daily import parse_months
from jobs.deal_archive import cutoff

KST = ZoneInfo("Asia/Seoul")
COLS = "apt_seq, contract_date::text AS contract_date, area_m2, price_10k, deal_type, is_cancelled"


def run(db: Db, store, today) -> int:
    cut = cutoff(today)
    old = [m for m in parse_months(f"202001-{cut}") if m < cut]
    rows: list[dict] = []
    for m in old:
        data = store.get(asset_name("deal", m))
        if data is None:
            print(f"  {asset_name('deal', m)} 없음", file=sys.stderr)
            return 1
        rows += decode(data)
    n_old = len(rows)
    for r in select(db, "SELECT DISTINCT contract_month AS m FROM deals ORDER BY 1"):
        rows += select(db, f"SELECT {COLS} FROM deals WHERE contract_month = {lit(r['m'])}")
    asof = select(db, "SELECT max(asof)::text AS d FROM dong_grade")[0]["d"]
    cx = {r["apt_seq"]: r for r in select(db, f"""SELECT c.apt_seq, g.grade, c.build_year, k.households FROM complexes c
        JOIN dong_grade g ON g.region_code = c.region_code AND g.umd_name = c.umd_name AND g.asof = DATE {lit(asof)}
        LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code""")}
    out = monthly(rows, cx)
    vals = ", ".join(f"({lit(m)}, {o['n_low']}, {o['h_low']}, {o['n_top']}, {o['h_top']}, {o['n_lip']}, {o['h_lip']}, DATE {lit(asof)})"
                     for m, o in out.items())
    db.query(f"BEGIN; DELETE FROM b5_history; INSERT INTO b5_history VALUES {vals}; COMMIT;")
    print(f"  거래 {len(rows):,}행 (보관 {n_old:,} + DB {len(rows) - n_old:,}), 급지 {asof}, {len(out)}개월")
    for m, o in out.items():
        lo = o["h_low"] * 100 / o["n_low"] if o["n_low"] else 0
        tp = o["h_top"] * 100 / o["n_top"] if o["n_top"] else 0
        lp = o["h_lip"] * 100 / o["n_lip"] if o["n_lip"] else 0
        print(f"  {m} 하위 {lo:5.1f}% ({o['n_low']:>6,}) 립밤 {lp:5.1f}% ({o['n_lip']:>5,}) 상위 {tp:5.1f}% ({o['n_top']:>5,}) 비 {lo / tp if tp else 0:.2f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    now = datetime.now(KST)
    print(f"[b5_history] {now:%Y-%m-%d %H:%M}")
    try:
        return run(connect(a.db), open_store(a.archive), now.date())
    except DbError as e:
        print(f"[b5_history] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
