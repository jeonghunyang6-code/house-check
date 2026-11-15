"""관심 단지 소식 모으기 (collector/complex_news.py → complex_news 0085). daily.yml 이 매일 돌린다.

관심 단지(user_state 'v2-watch2') + 내 단지('v2-my2')마다 네이버 뉴스를 단지 이름(따옴표)으로 최신순 검색한다.
처음(그 단지 기사가 없을 때)은 6개월 전까지 최대 10쪽(1,000건), 그 뒤엔 이미 받은 날짜까지만. 401·403·429 면 멈춘다.
200일 지난 기사는 지운다. 기사 본문은 저장하지 않는다(제목·링크·날짜·언론사·딱지).

    python -m jobs.complex_news [--db api]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from collector import complex_news as C
from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sources.naver_news import NewsBlocked, search

KST = ZoneInfo("Asia/Seoul")
PAGES = 10
KEEP_DAYS = 200


def targets(db: Db) -> list[dict]:
    st = {r["k"]: r["v"] for r in select(db, "SELECT k, v FROM user_state WHERE k IN ('v2-watch2', 'v2-my2')")}
    val = lambda v: json.loads(v) if isinstance(v, str) else v
    seqs = list(dict.fromkeys([*(val(st.get("v2-watch2")) or []), *([val(st["v2-my2"])] if st.get("v2-my2") else [])]))
    seqs = [s for s in seqs if isinstance(s, str) and s]
    if not seqs:
        return []
    return select(db, "SELECT apt_seq, apt_name, region_code, umd_name FROM complexes WHERE apt_seq IN (" + ", ".join(lit(s) for s in seqs) + ")")


def places(c: dict) -> tuple[str, ...]:
    """동·구 이름(짧은 단지 이름 확인용): '암사동'·'암사'·'강동구'·'강동'."""
    sgg = (REGIONS.get(c["region_code"], "").split() or [""])[-1]
    umd = c.get("umd_name") or ""
    return tuple(x for x in {umd, umd[:-1] if umd.endswith("동") else umd, sgg, sgg[:-1] if sgg[-1:] in "구시군" else sgg} if len(x) >= 2)


def collect(c: dict, since, today, sleep=time.sleep) -> list[dict]:
    names, pl = C.names_of(c["apt_seq"], c["apt_name"]), places(c)
    got: dict[str, dict] = {}
    for n in names:
        for p in range(PAGES):
            arts = search(f'"{n}"', start=1 + 100 * p)
            sleep(0.2)
            for a in arts:
                # 2026-11-15 사용자: 요약문에만 이름이 나온 기사(시장 정리·순위 기사)는 단지 소식이 아님 → 제목에 단지 이름이 있는 것만
                if a["pub"] < since or not a["id"] or a["id"] in got or not C.matches(a["text"], names, pl) or not C.in_title(a["title"], names):
                    continue
                got[a["id"]] = {"url": a["id"], "title": a["title"], "outlet": C.press_name(a["id"]), "pub": a["pub"],
                                "in_title": C.in_title(a["title"], names), "tags": C.tags_of(a["title"])}   # 딱지도 제목에서만(요약문 단어로 엉뚱한 딱지가 붙던 것)
            if len(arts) < 100 or min(a["pub"] for a in arts) < since:
                break
    return list(got.values())


def save(db: Db, seq: str, rows: list[dict], today) -> int:
    if not rows:
        return 0
    vals = ", ".join(f"({lit(seq)}, {lit(r['url'])}, {lit(r['title'])}, {lit(r['outlet'])}, {lit(r['pub'])}, {'true' if r['in_title'] else 'false'}, "
                     f"{lit(','.join(r['tags']) or None)}, {lit(today)})" for r in rows)
    have = {r["url"] for r in select(db, f"SELECT url FROM complex_news WHERE apt_seq = {lit(seq)}")}
    db.query("INSERT INTO complex_news (apt_seq, url, title, outlet, pub, in_title, tags, first_seen) VALUES " + vals + " ON CONFLICT (apt_seq, url) DO NOTHING;")
    return sum(1 for r in rows if r["url"] not in have)


def run(db: Db) -> int:
    today = datetime.now(KST).date()
    cs = targets(db)
    last = {r["apt_seq"]: r["d"] for r in select(db, "SELECT apt_seq, max(pub)::text d FROM complex_news GROUP BY apt_seq")}
    print(f"  관심·내 단지 {len(cs)}곳")
    try:
        for c in cs:
            since = C.cutoff(today) if c["apt_seq"] not in last else max(C.cutoff(today), datetime.fromisoformat(last[c["apt_seq"]]).date() - timedelta(days=2))
            rows = collect(c, since, today)
            print(f"  {c['apt_name']}: 맞는 기사 {len(rows)}건, 새로 {save(db, c['apt_seq'], rows, today)}건 (since {since})")
    except NewsBlocked as e:
        print(f"  멈춤: 뉴스 검색 {e}", file=sys.stderr)
    db.query(f"DELETE FROM complex_news WHERE pub < {lit(today - timedelta(days=KEEP_DAYS))} OR NOT in_title;")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db))
    except DbError as e:
        print(f"[complex_news] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
