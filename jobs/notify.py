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
from datetime import date, datetime, timedelta
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
    seqs = [str(s) for s in v if s]
    # 단지 번호가 바뀐 곳(재건축 새 단지 0072, 분양 단지가 실제 단지로 0070)은 새 번호로. 화면을 열면 서버 기록도 같은 규칙으로 바뀐다
    mp = {r["o"]: r["n"] for r in select(db, "SELECT old_seq o, new_seq n FROM complex_successor UNION ALL SELECT pc_seq, apt_seq FROM presale_complexes WHERE apt_seq IS NOT NULL")}
    return list(dict.fromkeys(mp.get(s, s) for s in seqs))


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


REDEV_NEAR_M = 2000   # 상세 탭 지도와 같은 반경


def redev_changes(db: Db, seqs: list[str]) -> list[dict]:
    """알리지 않은 정비구역 단계 변화(0077) 중 관심 단지 2km 안. 바로 전 단계가 있는 것만(처음 생긴 구역은 변화가 아님)."""
    if not seqs:
        return []
    ins = ", ".join(lit(s) for s in seqs)
    return select(db, f"""SELECT h.code, z.zone_nm, z.biz_type, h.stage, h.stage_no, p.stage prev, p.stage_no prev_no, h.first_seen::text d,
       (SELECT c.apt_name FROM complexes c WHERE c.apt_seq IN ({ins}) AND c.lat IS NOT NULL
          ORDER BY (c.lat - z.lat) ^ 2 + ((c.lng - z.lng) * 0.79) ^ 2 LIMIT 1) near_name
FROM redev_stage_hist h JOIN redev_zone z ON z.code = h.code AND z.stage = h.stage
JOIN LATERAL (SELECT stage, stage_no FROM redev_stage_hist p WHERE p.code = h.code AND p.stage <> h.stage AND p.first_seen < h.first_seen
              ORDER BY p.first_seen DESC LIMIT 1) p ON true
WHERE NOT h.notified AND z.lat IS NOT NULL AND EXISTS (SELECT 1 FROM complexes c WHERE c.apt_seq IN ({ins}) AND c.lat IS NOT NULL
  AND 6371000 * 2 * asin(sqrt(sin(radians(z.lat - c.lat) / 2) ^ 2 + cos(radians(c.lat)) * cos(radians(z.lat)) * sin(radians(z.lng - c.lng) / 2) ^ 2)) <= {REDEV_NEAR_M})
ORDER BY h.first_seen, z.zone_nm""")


def mark_redev(db: Db) -> None:
    db.query("UPDATE redev_stage_hist SET notified = true WHERE NOT notified;")


def daily(db: Db) -> str | None:
    seqs = watch(db)
    rows, mb, rd = deals(db, seqs, 1), db_mb(db), redev_changes(db, seqs)
    warn = [f"⚠️ DB {mb}MB / 500MB — 정리가 필요합니다(Claude 에게 'DB 정리')"] if mb >= DB_WARN_MB else []
    if not rows and not warn and not rd:
        return None
    url = site(db)
    head = [f"🔔 <b>관심 단지 새 거래 {len(rows)}건</b>", *deal_lines(rows)] if rows else []
    if rd:
        head += [f"🏗️ <b>주변 정비구역 단계 변화 {len(rd)}곳</b>"] + [
            f"{'⏫' if (r['stage_no'] or 0) > (r['prev_no'] or 0) else '🔁'} {html.escape(r['zone_nm'])}({html.escape(r['biz_type'] or '')}) "
            f"{html.escape(r['prev'])} → <b>{html.escape(r['stage'])}</b> · {html.escape(r['near_name'] or '')} 근처" for r in rd]
    return "\n".join(warn + head + ([f"\n{url}"] if url and (rows or rd) else []))


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
        out[s] = {"name": names.get(s, s), "px": px, "ask": ask, "ask_moved": moved, "ask_last": dates[-1] if dates else None}
    return out


def short_deal(r: dict) -> str:
    return (f"   🧾 {float(r['area_m2']):.0f}㎡ {r['floor']}층 <b>{eok(r['price_10k'])}</b>{tag(r)} · {r['cd'][5:].replace('-', '/')}"
            + (" · 직거래" if r["deal_type"] == "직거래" else "") + (f" · {r['kind']}" if r.get("kind") else ""))


RATIO_MOVE = 3.0   # 🔧 4주 전세가율 변화 알림 기준(%p). 책에 수치 없음


def jeonse_lines(db: Db, seqs: list[str], names: dict[str, str], today, save: bool = True) -> list[str]:
    """관심 단지 전세 신호만: 📖 전세가율 정상 범위 밖·80% 초과(p.152), 역전세(지금 전세 < 2년 전, 대비금 10%, p.153), 🔧 4주 전세가율 ±3%p.
    84㎡(없으면 59㎡)대 한 평형. 이번 값을 metric_snap 에 쌓는다."""
    if not seqs:
        return []
    ins = ", ".join(lit(s) for s in seqs)
    rows = {}
    for r in select(db, f"""SELECT apt_seq s, area_group ag, ref_10k, jeonse_10k, jeonse_ratio::float ratio, band_lo::float lo, band_hi::float hi, reverse_risk rr,
      jeonse_24m_10k j24, reserve_10k rs FROM complex_metrics WHERE apt_seq IN ({ins}) AND area_group IN (84, 85, 59, 60) AND jeonse_10k IS NOT NULL
      ORDER BY apt_seq, CASE WHEN area_group IN (84, 85) THEN 0 ELSE 1 END, jeonse_n DESC NULLS LAST"""):
        rows.setdefault(r["s"], r)
    if rows and save:
        db.query("INSERT INTO metric_snap (apt_seq, area_group, asof, ref_10k, jeonse_10k, jeonse_ratio) VALUES "
                 + ", ".join(f"({lit(r['s'])}, {r['ag']}, {lit(today)}, {lit(r['ref_10k'])}, {lit(r['jeonse_10k'])}, {lit(r['ratio'])})" for r in rows.values())
                 + " ON CONFLICT (apt_seq, area_group, asof) DO UPDATE SET ref_10k = EXCLUDED.ref_10k, jeonse_10k = EXCLUDED.jeonse_10k, jeonse_ratio = EXCLUDED.jeonse_ratio;")
    old = {(r["s"], r["ag"]): r["ratio"] for r in select(db, f"""SELECT DISTINCT ON (apt_seq, area_group) apt_seq s, area_group ag, jeonse_ratio::float ratio
      FROM metric_snap WHERE apt_seq IN ({ins}) AND asof <= {lit(today)}::date - 28 ORDER BY apt_seq, area_group, asof DESC""")}
    out = []
    for s in seqs:
        r = rows.get(s)
        if not r:
            continue
        sig = []
        if r["ratio"] is not None and r["ratio"] > 80:
            sig.append(f"⚠️ 전세가율 {r['ratio']:.0f}%(80% 초과)")
        elif r["ratio"] is not None and r["lo"] is not None and not (r["lo"] <= r["ratio"] <= r["hi"]):
            sig.append(f"전세가율 {r['ratio']:.0f}% · 정상 {r['lo']:.0f}~{r['hi']:.0f}%보다 {'높음' if r['ratio'] > r['hi'] else '낮음'}")
        o = old.get((s, r["ag"]))
        if o is not None and r["ratio"] is not None and abs(r["ratio"] - o) >= RATIO_MOVE:
            sig.append(f"{'📈' if r['ratio'] > o else '📉'} 4주 전 {o:.0f}% → {r['ratio']:.0f}%")
        if r["rr"]:
            sig.append(f"🚨 역전세: 지금 {eok(r['jeonse_10k'])} < 2년 전 {eok(r['j24'])} · 대비금 {eok(r['rs'])}")
        if sig:
            out.append(f"▪️ <b>{html.escape(names.get(s, s))}</b> {r['ag']}㎡ · " + " · ".join(sig))
    return out


ASK_STALE_DAYS = 14   # 이보다 오래 호가를 안 저장한 관심 단지는 주간 요약에서 챙김(매물 수 흐름이 끊기지 않게, 2026-10-26 사용자 요청)


def ask_reminder(info: dict[str, dict], seqs: list[str], today) -> list[str]:
    old = [(s, info[s]["ask_last"]) for s in seqs if info[s]["ask_last"] and (today - date.fromisoformat(info[s]["ask_last"])).days > ASK_STALE_DAYS]
    never = [s for s in seqs if not info[s]["ask_last"]]
    if not old and not never:
        return []
    out = [f"\n📝 <b>호가 저장 챙기기</b>(네이버 부동산 단지 화면에서 북마크)"]
    if old:
        out.append("   " + " · ".join(f"{html.escape(info[s]['name'])} {d[5:].replace('-', '/')}" for s, d in sorted(old, key=lambda x: x[1])) + f" ({ASK_STALE_DAYS}일 넘음)")
    if never:
        nm = [html.escape(info[s]["name"]) for s in never]
        out.append(f"   저장한 적 없음 {len(never)}곳: " + " · ".join(nm[:5]) + (f" 외 {len(nm) - 5}곳" if len(nm) > 5 else ""))
    return out


def weekly(db: Db, save: bool = True) -> str:
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
        out += ask_reminder(info, seqs, today)
    js = jeonse_lines(db, seqs, {k: v["name"] for k, v in info.items()}, today, save)
    if js:
        out.append("\n🔑 <b>전세 신호</b>")
        out += js
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
        text = {"daily": daily, "weekly": lambda d: weekly(d, save=not a.dry), "test": lambda _db: "house-check 알림 연결 확인 ✅"}[a.mode](db)
        if not text:
            print("  보낼 것 없음")
            if a.mode == "daily" and not a.dry:
                mark_redev(db)   # 관심 단지 근처 변화가 없으면 먼 구역 변화도 '알림 끝'
            return 0
        if a.dry:
            print(text)
            return 0
        got = T.send(db, text, force=a.mode == 'test')
        print(f"  {a.mode}: {got} ({len(text)}자)")
        if got == "sent" and a.mode == "daily":
            mark_redev(db)   # 보낸 뒤에만. 관심 단지에서 먼 구역의 변화도 같이 '알림 끝'(밀리지 않게)
    except (DbError, T.TelegramError) as e:
        print(f"[notify] 실패: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
