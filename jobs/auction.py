"""경매 낙찰가율 G6: 지지옥션 월간 경매동향 기사 → auction_stats (source='ggi_news', 시도, 아파트).

    python -m jobs.auction [--backfill 12]

📖 경매 낙찰가율 상승 = 상승장 초입, 하락 = 하락·보합 신호 (p.160~161). 기사 요약문에서 수치를 뽑고(collector/sources/auction_news.py),
같은 달·같은 지역에서 서로 다른 기사 2건 이상이 같은 값일 때만 확정한다. 기사는 다음 달 초에 나오므로 '발행월 − 1달'을 그 달 통계로 본다.
--backfill N: 'M월 아파트 낙찰가율' 식으로 지난 N개월을 따로 찾는다(검색 결과가 오래된 달일수록 적다).
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from datetime import date

from collector.db import Db, DbError, connect, lit
from collector.sources.auction_news import confirm, extract
from collector.sources.naver_news import NewsBlocked, search

QUERIES = ("지지옥션 아파트 낙찰가율", "서울 아파트 낙찰가율 지지옥션", "경기 아파트 낙찰가율 지지옥션", "인천 아파트 낙찰가율 지지옥션",
           "경매동향 아파트 낙찰가율", "수도권 아파트 낙찰가율", "경기도 아파트 낙찰가율", "경기 아파트 경매 낙찰가율 전월",
           "인천 아파트 경매 낙찰가율 전달", "인천 아파트 낙찰률 낙찰가율")
KEEP = ("서울", "경기", "인천", "전국")


def period_of(pub: date) -> str:
    y, m = (pub.year, pub.month - 1) if pub.month > 1 else (pub.year - 1, 12)
    return f"{y}-{m:02d}"


def collect(articles: list[dict]) -> dict[str, dict[str, tuple[float, str]]]:
    """기사 → {기간: {지역: (낙찰가율 %, 근거 기사 하나)}} (확정된 것만)."""
    by: dict[str, dict[str, list]] = defaultdict(dict)
    src: dict[tuple[str, str, float], str] = {}
    for a in articles:
        cands = [c for c in extract(a["text"]) if c.region in KEEP]
        if cands:
            per = period_of(a["pub"])
            by[per][a["id"]] = cands
            for c in cands:
                src.setdefault((per, c.region, c.ratio_pct), a["id"])
    out = {}
    for per, arts in by.items():
        got = confirm(arts)
        if got:
            out[per] = {r: (v, src[(per, r, v)]) for r, v in got.items()}
    return out


def run(db: Db, backfill: int) -> int:
    queries = list(QUERIES)
    today = date.today()
    for k in range(1, backfill + 1):
        y, m = today.year, today.month - k
        while m < 1:
            y, m = y - 1, m + 12
        queries += [f"{y}년 {m}월 아파트 낙찰가율 지지옥션", f"{m}월 서울 아파트 낙찰가율", f"{m}월 경기 아파트 낙찰가율",
                    f"{m}월 인천 아파트 낙찰가율"]
    arts, seen = [], set()
    try:
        for q in queries:
            for a in search(q):
                if a["id"] not in seen:
                    seen.add(a["id"])
                    arts.append(a)
            time.sleep(0.3)
    except NewsBlocked as e:
        print(f"  뉴스 검색 막힘: {e}", file=sys.stderr)
        return 2
    got = collect(arts)
    rows = [f"('ggi_news', {lit(per)}, {lit(r)}, 'sido', '아파트', {v / 100:.4f}, {lit(url)})"
            for per, regs in got.items() for r, (v, url) in regs.items()]
    if rows:
        db.query("BEGIN;\nINSERT INTO auction_stats (source, period_month, area_code, area_level, use_type, sale_ratio, source_url) VALUES "
                 + ", ".join(rows) + " ON CONFLICT (source, period_month, area_code, use_type) DO UPDATE SET sale_ratio = EXCLUDED.sale_ratio, "
                 "source_url = EXCLUDED.source_url;\nCOMMIT;")
    print(f"  기사 {len(arts)}건, 확정 {len(rows)}건: " + "; ".join(
        f"{per} " + ", ".join(f"{r} {v}" for r, (v, _) in sorted(regs.items())) for per, regs in sorted(got.items())))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=0)
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run(connect(a.db), a.backfill)
    except (DbError, OSError, KeyError) as e:
        print(f"[auction] 실패: {type(e).__name__} {e}", file=sys.stderr)
        rc = 1
    print(f"[auction] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
