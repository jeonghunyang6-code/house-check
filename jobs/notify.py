"""텔레그램 알림 (collector/telegram.py). notify.yml 이 부른다.

    python -m jobs.notify daily     # 매일 수집(daily-snapshot) 끝난 뒤: 관심 단지 새 실거래(급매·신고가 표시). 없으면 안 보냄
    python -m jobs.notify weekly    # 금요일 19시: 서울·경기·수도권 주간 매매 변동, 관심 단지 이번 주 거래, 정책 후보
    python -m jobs.notify test      # 연결 확인 한 줄

관심 단지 = 웹 화면에서 ♡ 한 단지(user_state 'v2-watch2'). 급매 = 그 단지·평형 기준 시세보다 5% 이상 싸게(1층·직거래 제외),
신고가 = 신고 당시 그 평형 최고가(prev_high_10k)보다 비싸게. 기준은 화면과 같다.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from collector import telegram as T
from collector.db import Db, DbError, connect, lit, select
from collector.policy import upcoming

KST = ZoneInfo("Asia/Seoul")
SITE = os.environ.get("HC_SITE_URL", "")   # 없으면 site.yml 이 배포 때 저장한 user_state 'site_url'


def eok(v) -> str:
    v = float(v)
    return f"{v / 10000:.2f}".rstrip("0").rstrip(".") + "억" if v >= 10000 else f"{v:,.0f}만"


def watch(db: Db) -> list[str]:
    got = select(db, "SELECT v FROM user_state WHERE k = 'v2-watch2'")
    if not got:
        return []
    v = got[0]["v"]
    v = json.loads(v) if isinstance(v, str) else v
    return [str(s) for s in v if s]


def tag(d: dict) -> str:
    p, ref, hi = float(d["price_10k"]), d.get("ref_10k"), d.get("prev_high_10k")
    out = []
    if hi and p > float(hi):
        out.append("🔺신고가")
    if ref and d["deal_type"] != "직거래" and str(d["floor"]) not in ("1", "-1") and p <= float(ref) * 0.95:
        out.append("🔻급매")
    gap = f" ({(p / float(ref) - 1) * 100:+.1f}%)" if ref else ""
    return gap + (" " + " ".join(out) if out else "")


def deals(db: Db, seqs: list[str], days: int) -> list[dict]:
    if not seqs:
        return []
    ins, since = ", ".join(lit(s) for s in seqs), f"(now() AT TIME ZONE 'Asia/Seoul')::date - {int(days)}"
    # 매매 + 분양권·입주권(0069, 신축·재건축은 등기 전까지 여기만). kind 가 있으면 권리 거래
    return select(db, f"""SELECT * FROM (
SELECT d.apt_seq, d.apt_name, d.area_m2, d.floor, d.price_10k, d.contract_date::text cd, d.deal_type, d.prev_high_10k, m.ref_10k, NULL::text kind
FROM deals d LEFT JOIN complex_metrics m ON m.apt_seq = d.apt_seq AND m.area_group = d.area_group
WHERE NOT d.is_cancelled AND d.apt_seq IN ({ins}) AND d.first_seen_date > {since}
UNION ALL
SELECT r.apt_seq, coalesce(k.kapt_name, r.apt_name), r.area_m2, r.floor, r.price_10k, r.contract_date::text, r.deal_type, NULL, NULL, r.kind
FROM right_deals r LEFT JOIN complexes c ON c.apt_seq = r.apt_seq LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
WHERE NOT r.is_cancelled AND (r.apt_seq IN ({ins}) OR r.pc_seq IN ({ins})) AND r.first_seen_date > {since}) x
ORDER BY apt_name, cd""")


def deal_lines(rows: list[dict]) -> list[str]:
    return [f"🏠 {html.escape(r['apt_name'])} {float(r['area_m2']):.0f}㎡ {r['floor']}층 <b>{eok(r['price_10k'])}</b>{tag(r)} · {r['cd'][5:]} 계약"
            + (" · 직거래" if r["deal_type"] == "직거래" else "") + (f" · {r['kind']}" if r.get("kind") else "") for r in rows]


def site(db: Db) -> str:
    if SITE:
        return SITE
    got = select(db, "SELECT v FROM user_state WHERE k = 'site_url'")
    v = got[0]["v"] if got else ""
    return json.loads(v) if isinstance(v, str) and v.startswith('"') else (v or "")


DB_WARN_MB = 450   # Supabase 무료 한도 500MB. 넘으면 매일 알림에 경고(정리 방법은 HANDOFF 'DB 용량')


def db_mb(db: Db) -> int:
    return int(select(db, "SELECT pg_database_size(current_database()) / 1048576 AS mb")[0]["mb"])


def daily(db: Db) -> str | None:
    rows, mb = deals(db, watch(db), 1), db_mb(db)
    warn = [f"⚠️ DB {mb}MB / 500MB — 정리가 필요합니다(Claude 에게 'DB 정리')"] if mb >= DB_WARN_MB else []
    if not rows and not warn:
        return None
    url = site(db)
    head = [f"🔔 <b>관심 단지 새 거래 {len(rows)}건</b>", *deal_lines(rows)] if rows else []
    return "\n".join(warn + head + ([f"\n{url}"] if url and rows else []))


def watch_info(db: Db, seqs: list[str]) -> dict[str, dict]:
    """관심 단지별 이름·가격(84㎡ 기준 시세, 없으면 최근 거래가)·저장 호가(84㎡대, 최근 두 번)."""
    if not seqs:
        return {}
    ins = ", ".join(lit(s) for s in seqs)
    names = {r["s"]: r["n"] for r in select(db, f"""SELECT c.apt_seq s, coalesce(CASE WHEN extract(year FROM k.use_date) > c.build_year + 10 THEN k.kapt_name END, c.apt_name) n
      FROM complexes c LEFT JOIN kapt_complexes k USING (kapt_code) WHERE c.apt_seq IN ({ins})
      UNION ALL SELECT pc_seq, apt_name FROM presale_complexes WHERE pc_seq IN ({ins})""")}
    refs = {}
    for r in select(db, f"SELECT apt_seq s, area_group ag, ref_10k p FROM complex_metrics WHERE apt_seq IN ({ins}) AND ref_10k IS NOT NULL ORDER BY abs(area_group - 84)"):
        refs.setdefault(r["s"], (r["ag"], r["p"]))
    last = {r["s"]: r for r in select(db, f"""SELECT DISTINCT ON (s) s, ag, p, k, d FROM (
      SELECT apt_seq s, area_group ag, price_10k p, '매매' k, contract_date d FROM deals WHERE apt_seq IN ({ins}) AND NOT is_cancelled AND area_group BETWEEN 75 AND 99
      UNION ALL SELECT coalesce(apt_seq, pc_seq), area_group, price_10k, kind, contract_date FROM right_deals
        WHERE (apt_seq IN ({ins}) OR pc_seq IN ({ins})) AND NOT is_cancelled AND area_group BETWEEN 75 AND 99) x ORDER BY s, d DESC""")}
    got = select(db, "SELECT v FROM user_state WHERE k = 'v2-naver'")
    asks = got[0]["v"] if got else {}
    asks = (json.loads(asks) if isinstance(asks, str) else asks) or {}
    week_ago = (datetime.now(KST).date() - timedelta(days=7)).isoformat()
    out = {}
    for s in seqs:
        if s in refs:
            px = f"{refs[s][0]}㎡ 기준 {eok(refs[s][1])}"
        elif s in last:
            px = f"최근 {last[s]['k']} {eok(last[s]['p'])}"
        else:
            px = "거래 없음"
        ask, moved = "", False
        dates = sorted(asks.get(s, {}))
        if dates:
            cnt = lambda d: sorted(x["p"] for x in asks[s][d] if x.get("t") == "매매" and x.get("ex") and 75 <= float(x["ex"]) < 100)
            now = cnt(dates[-1])
            if now:
                diff = len(now) - len(cnt(dates[-2])) if len(dates) > 1 else 0
                ask = f"🏷️ 호가 {len(now)}개 · 중간 {eok(now[(len(now) - 1) // 2])}" + (f" ({'+' if diff > 0 else ''}{diff}개)" if diff else "") + f" · {dates[-1][5:].replace('-', '/')} 저장"
                moved = diff != 0 and dates[-1] >= week_ago
        out[s] = {"name": names.get(s, s), "px": px, "ask": ask, "ask_moved": moved}
    return out


def short_deal(r: dict) -> str:
    return (f"   🧾 {float(r['area_m2']):.0f}㎡ {r['floor']}층 <b>{eok(r['price_10k'])}</b>{tag(r)} · {r['cd'][5:].replace('-', '/')}"
            + (" · 직거래" if r["deal_type"] == "직거래" else "") + (f" · {r['kind']}" if r.get("kind") else ""))


def weekly(db: Db) -> str:
    """금요일 주간 요약. 관심 단지는 이번 주 신고가 있거나 저장 호가 매물 수가 바뀐 곳만(2026-10-25 사용자 요청: 줄이고 이모지)."""
    today = datetime.now(KST).date()
    out = [f"📊 <b>주간 요약</b> · {today:%m/%d}"]
    wk = select(db, """SELECT cls_id, week_date::text d, value v FROM rone_weekly WHERE stat = 'sale' AND cls_id IN (50008, 50016, 50002)
      AND week_date >= (SELECT max(week_date) FROM rone_weekly WHERE stat = 'sale') - 7 ORDER BY cls_id, week_date""")
    names = {50008: "서울", 50016: "경기", 50002: "수도권"}
    by: dict[int, list] = {}
    for r in wk:
        by.setdefault(int(r["cls_id"]), []).append(float(r["v"]))
    parts = []
    for c in (50008, 50016, 50002):
        v = by.get(c, [])
        if len(v) >= 2:
            ch = (v[-1] / v[0] - 1) * 100
            parts.append(f"{'📈' if ch > 0 else '📉' if ch < 0 else '➖'} {names[c]} {ch:+.2f}%")
    if parts:
        out.append("  ".join(parts) + f"\n<i>부동산원 {wk[-1]['d'][5:].replace('-', '/')} 주</i>")
    seqs = watch(db)
    rows = deals(db, seqs, 7)
    info = watch_info(db, seqs)
    moved = [s for s in seqs if any(r["apt_seq"] == s for r in rows) or info[s]["ask_moved"]]
    if not seqs:
        out.append("\n🏠 관심 단지가 없습니다(웹에서 ♡)")
    else:
        out.append(f"\n🏠 <b>관심 단지 움직임</b> · {len(seqs)}곳 중 {len(moved)}곳")
        for s in moved:
            i, mine = info[s], [r for r in rows if r["apt_seq"] == s]
            out.append(f"\n▪️ <b>{html.escape(i['name'])}</b> · {i['px']}")
            out += [short_deal(r) for r in mine[:5]] + ([f"   … 외 {len(mine) - 5}건"] if len(mine) > 5 else [])
            if i["ask"]:
                out.append("   " + i["ask"])
        quiet = len(seqs) - len(moved)
        if quiet:
            out.append(f"\n😴 나머지 {quiet}곳: 이번 주 신고·호가 변동 없음")
    up = upcoming(today)
    pn = select(db, "SELECT kind, first_date::text d, n_press n FROM policy_news WHERE detected_at > now() - interval '7 days' AND known IS NULL ORDER BY first_date")
    if up or pn:
        out.append("\n📅 <b>정책</b>")
        out += [f"⏳ {d:%m/%d} (D-{(d - today).days}) {html.escape(t)}" for d, _, t, _ in up]
        out += [f"🆕 {r['d'][5:].replace('-', '/')} {r['kind']} 발표 후보 · 언론사 {r['n']}곳(확인 전)" for r in pn]
    mb = db_mb(db)
    url = site(db)
    out.append(f"\n{'⚠️' if mb >= DB_WARN_MB else '💾'} DB {mb}MB/500MB" + (f"  🔗 {url}" if url else ""))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["daily", "weekly", "test"])
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--dry", action="store_true", help="보내지 않고 글만 출력")
    a = ap.parse_args(argv)
    try:
        db = connect(a.db)
        text = {"daily": daily, "weekly": weekly, "test": lambda _db: "house-check 알림 연결 확인 ✅"}[a.mode](db)
        if not text:
            print("  보낼 것 없음")
            return 0
        if a.dry:
            print(text)
            return 0
        print(f"  {a.mode}: {T.send(db, text, force=a.mode == 'test')} ({len(text)}자)")
    except (DbError, T.TelegramError) as e:
        print(f"[notify] 실패: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
