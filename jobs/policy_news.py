"""정책 발표 감지 (collector/policy_news.py → policy_news, 0067). policy_news.yml 이 하루 두 번 돈다.

새 후보(이미 아는 사건과 겹치지 않고, 같은 종류로 ±3일 안에 올린 적 없는 것)가 있으면 --issue-file 에 알림 글을 쓴다
→ 워크플로가 GitHub 이슈로 올려 사용자에게 알림. 확인 뒤 collector/policy.py 에 넣고 status='added'.

자동 추가(2026-11-02 사용자 요청, 0082): 후보가 언론사 🔧5곳 이상·이틀 이상 보도되면 status='auto' → 화면 정책 목록에 '자동' 표시로 바로 들어가고
텔레그램으로 알린다(틀리면 답장 '빼줘' → web/lib/tgreply.js 가 'removed'). 정책브리핑 보도자료와 맞으면 official 을 채워 '자동' 표시를 뗀다.

    python -m jobs.policy_news [--issue-file new.md] [--days 3]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from collector import newtown_news as N
from collector import official as O
from collector import policy_news as P
from collector import telegram as T
from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sources.naver_news import NewsBlocked, search

KST = ZoneInfo("Asia/Seoul")
SAME = 3   # 같은 종류로 이 날짜 차이 안이면 같은 후보로 본다
AUTO_PRESS = 5   # 🔧 자동 추가: 서로 다른 언론사 수(후보 기준 3곳보다 높게)
AUTO_DAYS = 2    # 🔧 자동 추가: 결정 기사가 나온 날 수(첫날 ~ 마지막 날)


def fetch(pages: int = 2, queries=P.QUERIES) -> list[dict]:
    arts = []
    for q in queries:
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
            f"{lit(json.dumps([{'d': str(d), 't': t, 'u': u} for d, t, u in c.titles[:8]], ensure_ascii=False))}::jsonb, {lit(c.known)}, "
            f"{lit(max(d for d, _, _ in c.titles))})"
            for c in cands]
    # 다시 볼 때마다 최근 days 일 기사만 세므로 언론사 수가 줄어든다(12곳 → 4곳, 2026-11-02) → 가장 컸던 값을 남긴다
    db.query("INSERT INTO policy_news (kind, first_date, n_press, regions, articles, known, last_date) VALUES " + ", ".join(rows)
             + " ON CONFLICT (kind, first_date) DO UPDATE SET n_press = GREATEST(policy_news.n_press, EXCLUDED.n_press), "
               "regions = coalesce(EXCLUDED.regions, policy_news.regions), "
               "articles = CASE WHEN jsonb_array_length(EXCLUDED.articles) >= jsonb_array_length(policy_news.articles) THEN EXCLUDED.articles ELSE policy_news.articles END, "
               "known = EXCLUDED.known, last_date = GREATEST(policy_news.last_date, EXCLUDED.last_date), updated_at = now();")
    return new


def promote(db: Db, today) -> list[dict]:
    """status='new' 후보 중 언론사 AUTO_PRESS 곳·AUTO_DAYS 일 이상이면 'auto'. 같은 종류 ±SAME 일에 이미 auto·added·removed 가 있으면 건너뜀."""
    rows = select(db, f"""SELECT kind, first_date::text d, n_press n, articles->0->>'t' head FROM policy_news p
      WHERE status = 'new' AND known IS NULL AND n_press >= {AUTO_PRESS} AND last_date >= first_date + {AUTO_DAYS - 1}
        AND first_date > {lit(today)}::date - 30
        AND NOT EXISTS (SELECT 1 FROM policy_news o WHERE o.kind = p.kind AND o.status IN ('auto', 'added', 'removed')
                        AND abs(o.first_date - p.first_date) <= {SAME})
      ORDER BY first_date""")
    out = []
    for r in rows:
        if any(o["kind"] == r["kind"] and abs((datetime.fromisoformat(o["d"]) - datetime.fromisoformat(r["d"])).days) <= SAME for o in out):
            continue   # 같은 사건이 첫날만 달리 두 줄로 쌓인 경우 앞의 것만
        r["title"] = title_of(r["head"])
        db.query(f"UPDATE policy_news SET status = 'auto', title = {lit(r['title'])}, auto_at = now() WHERE kind = {lit(r['kind'])} AND first_date = {lit(r['d'])};")
        out.append(r)
    return out


def title_of(t: str | None) -> str:
    """기사 제목 → 화면 제목: 머리말([단독] 등)·콜론을 빼고 🔧50자."""
    t = re.sub(r"\s*:\s*", " ", re.sub(r"^\s*(\[[^\]]*\]|【[^】]*】|<[^>]*>)\s*", "", (t or "").strip())).strip()
    return t[:50] + ("…" if len(t) > 50 else "")


def official_check(db: Db, today) -> None:
    """'auto' 이고 공식 확인 안 된 최근 2주 줄을 정책브리핑 보도자료와 대조(collector/official.py). 피드를 못 받으면 건너뜀."""
    if not O.FEEDS:   # 정책브리핑 RSS 중단(2026-11-02 확인) → 공식 확인 꺼짐
        return
    rows = select(db, f"SELECT kind, first_date::text d FROM policy_news WHERE status = 'auto' AND official IS NULL AND first_date > {lit(today)}::date - 14")
    if not rows:
        return
    items, errs = O.fetch()
    print(f"  공식 보도자료 {len(items)}건" + (f", 못 받은 피드 {len(errs)}: " + "; ".join(errs) if errs else ""))
    for r in rows:
        m = O.match(r["kind"], datetime.fromisoformat(r["d"]).date(), items)
        if m:
            db.query(f"UPDATE policy_news SET official = {lit(json.dumps(m, ensure_ascii=False))}::jsonb WHERE kind = {lit(r['kind'])} AND first_date = {lit(r['d'])};")
            print(f"   공식 확인 {r['kind']} {r['d']}: {m['t'][:60]}")


def auto_msg(rows: list[dict]) -> str:
    """텔레그램 알림. 'MM/DD 종류' 꼴을 tgreply.js 의 '빼줘' 처리가 읽는다."""
    return ("<b>📌 정책 자동 추가</b>(언론사 5곳+·이틀 이상 보도)\n" + "\n".join(
        f"• {r['d'][5:].replace('-', '/')} {r['kind']} · 언론사 {r['n']}곳: {html.escape(r['title'])}" for r in rows)
        + "\n틀리면 이 메시지에 답장으로 '빼줘'")


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
    auto = promote(db, today)
    if auto:
        print("  자동 추가:", ", ".join(f"{r['kind']} {r['d']}" for r in auto))
        if T.enabled():
            try:
                print("  텔레그램:", T.send(db, auto_msg(auto)))
            except T.TelegramError as e:
                print(f"  텔레그램 실패: {e}", file=sys.stderr)
    official_check(db, today)
    newtown(db, today, days)
    return 0


NT_SEEN = "nt_news_seen"   # user_state: 이미 알린 '구역|단계'


def newtown(db: Db, today, days: int) -> None:
    """1기 신도시 선도지구 단계 변화 후보(collector/newtown_news.py) → 텔레그램. 확인 뒤 collector/newtown.py 를 손으로 고친다."""
    try:
        arts = fetch(1, N.QUERIES)
    except NewsBlocked as e:
        print(f"  선도지구 뉴스 검색 막힘: {e}", file=sys.stderr)
        return
    got = select(db, f"SELECT v FROM user_state WHERE k = {lit(NT_SEEN)}")
    seen = set((json.loads(got[0]["v"]) if isinstance(got[0]["v"], str) else got[0]["v"]) or []) if got else set()
    cands = N.candidates(arts, today, days)
    new = [c for c in cands if f"{c.code}|{c.stage}" not in seen]
    print(f"  선도지구 기사 {len(arts):,}건, 후보 {len(cands)}건, 새 알림 {len(new)}건" + "".join(f"\n   {c.zone_nm} → {c.stage} 언론사 {len(c.press)}" for c in cands))
    if not new:
        return
    if T.enabled():
        try:
            print("  텔레그램:", T.send(db, "<b>🏙️ 선도지구 단계 후보</b>(기사 확인 뒤 Claude 에게 '선도지구 반영')\n" + "\n".join(
                f"• {c.zone_nm} → {c.stage} · 언론사 {len(c.press)}곳: {c.titles[0][1][:60]}" for c in new)))
        except T.TelegramError as e:
            print(f"  텔레그램 실패: {e}", file=sys.stderr)
            return
    seen |= {f"{c.code}|{c.stage}" for c in new}
    db.query(f"INSERT INTO user_state (k, v) VALUES ({lit(NT_SEEN)}, {lit(json.dumps(sorted(seen), ensure_ascii=False))}::jsonb) "
             "ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now();")


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
