"""정책 발표 감지 (collector/policy_news.py → policy_news, 0067). policy_news.yml 이 하루 두 번 돈다.

새 후보(이미 아는 사건과 겹치지 않고, 같은 종류로 ±3일 안에 올린 적 없는 것)가 있으면 --issue-file 에 알림 글을 쓴다
→ 워크플로가 GitHub 이슈로 올려 사용자에게 알림. 확인 뒤 collector/policy.py 에 넣고 status='added'.

    python -m jobs.policy_news [--issue-file new.md] [--days 3]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from collector import policy_news as P
from collector import telegram as T
from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sources.naver_news import NewsBlocked, search

KST = ZoneInfo("Asia/Seoul")
SAME = 3   # 같은 종류로 이 날짜 차이 안이면 같은 후보로 본다


def fetch(pages: int = 2) -> list[dict]:
    arts = []
    for q in P.QUERIES:
        for p in range(pages):
            arts += search(q, start=1 + 100 * p)
            time.sleep(0.2)
    return arts


def region_names(codes: list[str]) -> str:
    if len(codes) >= 20:
        return f"{len(codes)}개 시군구"
    return ", ".join(REGIONS.get(c, c) for c in codes)


def save(db: Db, cands: list[P.Cand]) -> list[P.Cand]:
    """후보를 쌓고, 처음 보는(새 알림이 필요한) 것만 돌려준다."""
    if not cands:
        return []
    old = select(db, "SELECT kind, first_date::text AS d FROM policy_news WHERE first_date > current_date - 30")
    def seen(c): return any(o["kind"] == c.kind and abs((datetime.fromisoformat(o["d"]).date() - c.first).days) <= SAME for o in old)
    new = [c for c in cands if not seen(c)]
    rows = [f"({lit(c.kind)}, {lit(c.first)}, {len(c.press)}, {lit(','.join(c.region_codes()) or None)}, "
            f"{lit(json.dumps([{'d': str(d), 't': t, 'u': u} for d, t, u in c.titles[:8]], ensure_ascii=False))}::jsonb, {lit(c.known)})"
            for c in cands]
    db.query("INSERT INTO policy_news (kind, first_date, n_press, regions, articles, known) VALUES " + ", ".join(rows)
             + " ON CONFLICT (kind, first_date) DO UPDATE SET n_press = EXCLUDED.n_press, regions = EXCLUDED.regions, "
               "articles = EXCLUDED.articles, known = EXCLUDED.known, updated_at = now();")
    return new


def issue_md(new: list[P.Cand]) -> str:
    out = ["뉴스에서 새로 결정된 것으로 보이는 부동산 정책입니다. 기사를 확인한 뒤 정책 이력(collector/policy.py)에 넣을지 정해 주세요.", ""]
    for c in new:
        out.append(f"### {c.kind} · {c.first} · 언론사 {len(c.press)}곳" + (f" · 지역: {region_names(c.region_codes())}" if c.region_codes() else ""))
        if c.known:
            out.append(f"- 이미 있는 비슷한 사건: {c.known}")
        for d, t, u in c.titles[:5]:
            out.append(f"- {d} [{t[:90]}]({u})")
        out.append("")
    out.append("판정: 기사 제목·요약문의 결정 문장(지정한다·시행키로 + 날짜) 기준, 같은 종류 언론사 3곳 이상. 기사 본문은 열지 않음.")
    return "\n".join(out)


def run(db: Db, days: int, issue_file: str | None) -> int:
    today = datetime.now(KST).date()
    try:
        arts = fetch()
    except NewsBlocked as e:
        print(f"  뉴스 검색 막힘: {e}", file=sys.stderr)
        return 2
    cands = P.candidates(arts, today, days)
    new = [c for c in save(db, cands) if not c.known]
    print(f"  기사 {len(arts):,}건(가장 오래된 {min((a['pub'] for a in arts), default=today)}), 후보 {len(cands)}건, 새 알림 {len(new)}건")
    for c in cands:
        print(f"   {c.kind} {c.first} 언론사 {len(c.press)} {'이미 있음: ' + c.known[:40] if c.known else ''}")
    if new and T.enabled():
        try:
            print("  텔레그램:", T.send(db, "<b>새 정책 후보</b>\n" + "\n".join(f"• {c.first} {c.kind} · 언론사 {len(c.press)}곳: {c.titles[0][1][:60]}" for c in new)))
        except T.TelegramError as e:
            print(f"  텔레그램 실패: {e}", file=sys.stderr)
    if issue_file:
        with open(issue_file, "w", encoding="utf-8") as f:
            f.write(issue_md(new) if new else "")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--issue-file")
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.days, a.issue_file)
    except DbError as e:
        print(f"[policy_news] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
