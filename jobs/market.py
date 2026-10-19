"""시장 국면·체크리스트 신호 계산 (collector/market.py, 0011). rone weekly 뒤에 돈다.

    python -m jobs.market

region_phase: 지역별 B1 국면·B3 낙폭 (매매·전세)
market_signals: 홈 체크리스트 (서울·수도권 국면, B4 하락 분류 조건, B5 상승 지역 비율, 매매수급지수)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from collector.db import Db, DbError, connect, lit, select
from collector.market import (_shift, B5_HOT, B5_SPREAD, B5_WATCH, b4_applies, b5_state, rebound_state, DOWN_RATIO, JEONSE_WEEKS, SUPPLY_WEEKS, UNEMP_JUMP, b4, loan_growth, new_jeonse, rate_price_relation, yoy_series, monthly, mortgage_band, phase, run_length,
                             unemployment)

SEOUL, CAPITAL = 50008, 50002


def series(db: Db, stat: str, months: int = 30) -> dict[int, list[tuple[date, float]]]:
    rows = select(db, f"SELECT cls_id, week_date::text AS d, value FROM rone_weekly WHERE stat = {lit(stat)} "
                      f"AND week_date >= (SELECT max(week_date) FROM rone_weekly WHERE stat = {lit(stat)}) - {months * 31} "
                      "ORDER BY cls_id, week_date")
    out: dict[int, list[tuple[date, float]]] = {}
    for r in rows:
        out.setdefault(r["cls_id"], []).append((date.fromisoformat(r["d"]), float(r["value"])))
    return out


def macro(db: Db, series: str, n: int) -> list[tuple[str, float]]:
    """macro_monthly 최근 n개월 (오래된 것부터)."""
    rows = select(db, f"SELECT period, value FROM macro_monthly WHERE series = {lit(series)} ORDER BY period DESC LIMIT {int(n)}")
    return [(r["period"], float(r["value"])) for r in rows][::-1]


def _ym(p: str) -> str:
    return f"{p[:4]}.{p[4:]}"


BANDS = ("6억 미만", "6~9억", "9~15억", "15~25억", "25~30억", "30억+")   # 15·25억 = 주담대 한도 경계, 30억 = 급지 1급(E1)·초고가(L6)
BAND_CUTS = (60000, 90000, 150000, 250000, 300000)


def price_bands(db: Db) -> list[dict]:
    """가격대(84㎡ 환산 기준 시세)별 B1 12개월 변화 중앙값, 최근 3개월 상승 비중. 단지마다 84㎡ 에 가장 가까운 면적군 하나."""
    case = " ".join(f"WHEN p84 < {c} THEN {lit(b)}" for c, b in zip(BAND_CUTS, BANDS)) + f" ELSE {lit(BANDS[-1])}"
    rows = select(db, f"""
WITH m AS (SELECT DISTINCT ON (apt_seq) apt_seq, left(apt_seq, 2) AS sd, ref_10k::numeric / area_group * 84 AS p84, chg_12m, last3
  FROM complex_metrics WHERE ref_10k IS NOT NULL AND area_group BETWEEN 59 AND 135 AND chg_12m IS NOT NULL
  ORDER BY apt_seq, abs(area_group - 84))
SELECT CASE WHEN sd = '11' THEN '서울' ELSE '경기·인천' END AS scope, CASE {case} END AS band, count(*) AS n,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY chg_12m) AS chg, avg((last3 = '상승')::int) * 100 AS up3
FROM m GROUP BY 1, 2""")
    out = [dict(scope=r["scope"], band=r["band"], n=int(r["n"]), chg=round(float(r["chg"]), 1), up3=round(float(r["up3"])))
           for r in rows if int(r["n"]) >= 5]   # 🔧 5곳 미만 구간은 뺀다
    return sorted(out, key=lambda b: (b["scope"] != "서울", BANDS.index(b["band"])))


def run(db: Db) -> dict[str, tuple]:
    today = date.today()
    stmts = ["BEGIN;", "DELETE FROM region_phase;"]
    phases: dict[tuple[str, int], object] = {}
    c13s: dict[tuple[str, int], float | None] = {}
    asof = None
    for stat in ("sale", "jeonse"):
        ser = series(db, stat)
        vals = []
        for cid, pts in ser.items():
            ph = phase(monthly(pts))
            phases[(stat, cid)] = ph
            asof = max(asof or pts[-1][0], pts[-1][0])
            c13 = round((pts[-1][1] / pts[-14][1] - 1) * 100, 2) if len(pts) >= 14 and pts[-14][1] else None
            c13s[(stat, cid)] = c13
            vals.append("(" + ", ".join(lit(v) for v in (stat, cid, pts[-1][0], ph.chg_12m, ph.up_months, ph.down_months,
                                                        ph.last3, ph.phase, ph.drawdown, c13)) + ")")
        if vals:
            stmts.append("INSERT INTO region_phase (stat, cls_id, asof, chg_12m, up_months, down_months, last3, phase, drawdown, chg_13w) VALUES "
                         + ", ".join(vals) + ";")

    sig: dict[str, tuple] = {}  # key → (value, state, detail)
    for cid, nm in ((SEOUL, "seoul"), (CAPITAL, "sudo")):
        ph = phases.get(("sale", cid))
        if ph:
            sig[f"b1_{nm}"] = (ph.chg_12m, ph.phase, f"12개월 {ph.chg_12m:+.2f}%, 상승 {ph.up_months}개월·하락 {ph.down_months}개월, 최근 3개월 {ph.last3}"
                               if ph.chg_12m is not None else "12개월 데이터 부족")
            sig[f"b3_{nm}"] = (ph.drawdown, "20% 이상" if (ph.drawdown or 0) >= 20 else "10% 이상" if (ph.drawdown or 0) >= 10
                               else "5% 이상" if (ph.drawdown or 0) >= 5 else "5% 미만", "최근 24개월 최고 대비")

    # B4 ① 전국 하락 지역 비율 4주 평균
    br = select(db, "SELECT week_date::text AS d, n, n_down, n_up FROM rone_breadth WHERE stat = 'sale' AND scope = '전국' "
                    "ORDER BY week_date DESC LIMIT 4")
    ratio4 = round(sum(r["n_down"] * 100.0 / r["n"] for r in br) / len(br), 1) if len(br) == 4 else None
    # B4 ② 수도권 전세 연속 하락 주
    jser = [v for _, v in series(db, "jeonse", 6).get(CAPITAL, [])]
    jdown = run_length(jser, -1) if len(jser) > JEONSE_WEEKS else None
    # B4 ③ / G5 실업률 (jobs/macro.py)
    um = unemployment(macro(db, "unemployment_sa", 4))
    met, known, cls = b4(ratio4, jdown, um.b4_met if um else None)
    sudo_ph = phases.get(("sale", CAPITAL))
    sudo_phase = getattr(sudo_ph, "phase", None)
    falling = b4_applies(sudo_ph)
    sig["b4_down_ratio"] = (ratio4, "데이터 없음" if ratio4 is None else "충족" if ratio4 >= DOWN_RATIO else "미충족",
                            f"전국 시군구 중 주간 하락 지역 비율 최근 4주 평균 (기준 {DOWN_RATIO:.0f}%)")
    sig["b4_jeonse_8w"] = (jdown, "데이터 없음" if jdown is None else "충족" if jdown >= JEONSE_WEEKS else "미충족",
                           f"수도권 전세지수 연속 하락 주 (기준 {JEONSE_WEEKS}주). 2012년 이후 4번 켜짐: 2012-07·2018-12·2022-03 뒤 매매 하락, 2018-01 은 상승")
    if um:
        chg = f"{um.chg_3m:+.1f}%p" if um.chg_3m is not None else "비교 불가"
        sig["b4_unemployment"] = (um.rate, "충족" if um.b4_met else "미충족",
                                  f"{_ym(um.period)} 계절조정 실업률 {um.rate}%, 3개월 전 대비 {chg} (기준 4% 또는 +{UNEMP_JUMP}%p)")
        sig["g5_unemployment"] = (um.rate, um.band, f"{_ym(um.period)} 계절조정 실업률. 4% 미만 안정, 4~6% 경기침체, 6% 이상 경제 위기")
    else:
        sig["b4_unemployment"] = (None, "데이터 없음", "실업률 4% 이상 또는 3개월 +0.5%p (macro_monthly 비어 있음)")
        sig["g5_unemployment"] = (None, "데이터 없음", "계절조정 실업률")
    sig["b4_class"] = (met, cls if falling else "해당 없음",
                       f"수도권 국면 {sudo_phase}. 하락장·일시 조정 또는 최근 3개월 연속 하락일 때만 판정. 조건 {met}/{known}개 충족 (판단 가능 {known}/3)")
    # D5 서울 신규 전세 감소 + 전세가 상승 (rent_region_month: 시군구 × 달 합계, 전체 기간 0053)
    last_complete = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)  # 지지난 달 말
    cnt = {r["m"]: (int(r["jn"]), int(r["jr"])) for r in select(
        db, "SELECT contract_month AS m, sum(n_jeonse_new) AS jn, sum(n_jeonse_renew) AS jr FROM rent_region_month "
            "WHERE region_code LIKE '11%' AND contract_month >= '202106' GROUP BY 1")}
    js = [v for _, v in series(db, "jeonse", 6).get(SEOUL, [])]
    jchg = round((js[-1] / js[-14] - 1) * 100, 2) if len(js) >= 14 else None
    nj = new_jeonse(cnt, last_complete.strftime("%Y%m"), jchg)
    sig["d5_new_jeonse"] = (nj.yoy, nj.state,
                            f"서울 신규 전세 {_ym(nj.months[0])}~{_ym(nj.months[-1])} {nj.n_new:,}건, 1년 전 {nj.n_new_prev:,}건 "
                            f"({nj.yoy:+.1f}%), 갱신 비중 {nj.renew_share}%, 서울 전세지수 13주 {nj.jeonse_chg:+.2f}%. 신규 감소 + 전세가 상승이면 충족"
                            if nj.yoy is not None and nj.jeonse_chg is not None else "서울 신규 전세 건수·전세지수")
    # D2 4분면 (▶ J2): 수도권 시군구 중 13주 매매↓·전세↑ ("부의 사다리" 칸)
    q = [{"full_name": r["full_name"], "s": c13s.get(("sale", r["cls_id"])), "j": c13s.get(("jeonse", r["cls_id"]))}
         for r in select(db, "SELECT cls_id, full_name FROM rone_regions WHERE region_code IS NOT NULL")]
    q = [r for r in q if r["s"] is not None and r["j"] is not None]
    if q:
        quad = {"매매↓전세↑": 0, "매매↑전세↑": 0, "매매↑전세↓": 0, "매매↓전세↓": 0}
        ladder = []
        for r in q:
            sv, jv = float(r["s"]), float(r["j"])
            k = ("매매↑" if sv >= 0 else "매매↓") + ("전세↑" if jv >= 0 else "전세↓")
            quad[k] += 1
            if k == "매매↓전세↑":
                ladder.append(r["full_name"].rsplit(">", 1)[-1])
        sig["d2_ladder"] = (quad["매매↓전세↑"], "있음" if ladder else "없음",
                            f"수도권 {len(q)}곳 최근 13주: 매매↓전세↑ {quad['매매↓전세↑']}곳"
                            + (f"({', '.join(ladder[:8])}{' 외' if len(ladder) > 8 else ''})" if ladder else "")
                            + f", 매매↑전세↑ {quad['매매↑전세↑']}, 매매↑전세↓ {quad['매매↑전세↓']}, 매매↓전세↓ {quad['매매↓전세↓']}")
    else:
        sig["d2_ladder"] = (None, "데이터 없음", "매매·전세 4분면")
    # F2 인허가·착공 (📖 p.54~56): 수도권 아파트 최근 12개월 합계 vs 그 전 12개월. 공급 효과는 지역마다 반대라 판정 없이 참고
    for key, name, label in (("f2_permits", "permits_sudo", "인허가"), ("f2_starts", "starts_sudo", "착공")):
        m = macro(db, name, 24)
        if len(m) == 24:
            a, b = sum(v for _, v in m[12:]), sum(v for _, v in m[:12])
            chg = round((a / b - 1) * 100, 1) if b else None
            sig[key] = (round(a), "감소" if chg is not None and chg < 0 else "증가",
                        f"수도권 아파트 {label} {_ym(m[12][0])}~{_ym(m[-1][0])} {a:,.0f}호, 그 전 12개월 {b:,.0f}호 ({chg:+.1f}%). "
                        "대기 수요가 많은 곳은 입주장만 전세↓, 적은 곳은 매매·전세 모두↓(📖 p.54~56)")
        else:
            sig[key] = (None, "데이터 없음", f"수도권 아파트 {label}")
    # F3 미분양 (📖 원인 5가지 p.155~160): 수도권 합계와 준공 후 미분양, 1년 전 대비
    tot = {}
    for kind in ("unsold", "unsold_done"):
        ser = [dict(macro(db, f"{kind}_{sd}", 13)) for sd in ("seoul", "incheon", "gyeonggi")]
        common = sorted(set.intersection(*(set(x) for x in ser))) if all(ser) else []
        tot[kind] = [(p, sum(x[p] for x in ser)) for p in common]
    u, ud = tot["unsold"], tot["unsold_done"]
    if len(u) == 13 and ud:
        chg = round((u[-1][1] / u[0][1] - 1) * 100, 1) if u[0][1] else None
        sig["f3_unsold"] = (round(u[-1][1]), "증가" if chg is not None and chg > 0 else "감소",
                            f"{_ym(u[-1][0])} 수도권 미분양 {u[-1][1]:,.0f}호(1년 전 {u[0][1]:,.0f}호, {chg:+.1f}%), 그중 준공 후 {ud[-1][1]:,.0f}호. "
                            "원인(분양가·입지·상품성·공급 집중·거시)은 단지별로 봐야 한다(📖 p.155~160)")
    else:
        sig["f3_unsold"] = (None, "데이터 없음", "수도권 미분양")
    # L9 가격대별 시장 (▶ 금리상승의 후폭풍 4:36 "고가 꺾임, 저가 상승, 중간 숨고르기" / 📖 p.152), L6 초고가 분리(📖 p.122)
    bands = price_bands(db)
    se = [b for b in bands if b["scope"] == "서울"]
    if se:
        hi_, mid_ = [b for b in se if b["band"] in BANDS[-2:]], [b for b in se if b["band"] in BANDS[2:4]]
        def med(bs):
            n = sum(b["n"] for b in bs)
            return sum(b["chg"] * b["n"] for b in bs) / n if n else None
        h, m_ = med(hi_), med(mid_)
        state = "고가 덜 오름" if h is not None and m_ is not None and h < m_ - 3 else "고가 더 오름" if h is not None and m_ is not None and h > m_ + 3 else "비슷"
        sig["l9_price_bands"] = (round(h - m_, 1) if h is not None and m_ is not None else None, state,
                                 "서울 단지 12개월 변화 중앙값(84㎡ 환산 기준 시세 구간, B1 판정 단지): "
                                 + " · ".join(f"{b['band']} {b['chg']:+.1f}%({b['n']}곳)" for b in se)
                                 + ". 🔧 25억+ 와 9~25억 차이 ±3%p. ▶ 가격대마다 다른 시장(고가 꺾임·저가 상승·중간 숨고르기), 📖 초고가는 따로 본다 p.122")
    # A4 급매 체결 비중 (📖 급매 = 실거래 대비 5% 이상 저렴 p.245~247): 서울 최근 4주 중개 거래 중
    # 같은 단지·면적의 직전 90일 중앙값(3건 이상) × 0.95 이하. 1층은 판정·기준 모두에서 뺀다(A1 과 같게, 1층은 평소 약 8% 낮아
    # 넣으면 41%가 급매로 잡혔다, 2026-10-18). 2~4층 할인(3~5%)은 남는다. 경기·인천은 이력이 짧아 제외
    a4 = select(db, f"""WITH r AS (
        SELECT d.apt_seq, d.area_group, d.contract_date, d.price_10k FROM deals d
        WHERE d.region_code LIKE '11%' AND NOT d.is_cancelled AND d.deal_type = '중개' AND d.floor IS DISTINCT FROM 1
          AND d.contract_date > {lit(today)}::date - 56),
      p AS (SELECT r.contract_date, r.price_10k, x.ref, x.n FROM r CROSS JOIN LATERAL (
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY b.price_10k) AS ref, count(*) AS n FROM deals b
        WHERE b.apt_seq = r.apt_seq AND b.area_group = r.area_group AND NOT b.is_cancelled AND b.deal_type = '중개' AND b.floor IS DISTINCT FROM 1
          AND b.contract_date < r.contract_date AND b.contract_date >= r.contract_date - 90) x)
      SELECT (contract_date > {lit(today)}::date - 28) AS cur, count(*) FILTER (WHERE n >= 3) AS total,
             count(*) FILTER (WHERE n >= 3 AND price_10k <= ref * 0.95) AS gm FROM p GROUP BY 1""")
    g = {r["cur"]: r for r in a4}
    cur, prev = g.get(True), g.get(False)
    if cur and cur["total"]:
        rc = round(cur["gm"] * 100.0 / cur["total"], 1)
        rp = round(prev["gm"] * 100.0 / prev["total"], 1) if prev and prev["total"] else None
        sig["a4_quick_sale"] = (rc, "참고" if rp is None else "감소" if rc < rp else "증가" if rc > rp else "유지",
                                f"서울 최근 4주 중개 거래(1층 제외) {cur['total']:,}건 중 직전 시세보다 5% 이상 싸게 팔린 거래 {cur['gm']:,}건 ({rc}%)"
                                + (f", 그 전 4주 {rp}%" if rp is not None else "")
                                + ". 급매가 소진되고 하단이 오르면 반등(📖 p.245~247). 최근 거래는 신고 기한(30일) 전이라 더 늘어난다")
    else:
        sig["a4_quick_sale"] = (None, "데이터 없음", "서울 급매 체결 비중")
    # C5 직거래 비중 (📖 하락기에 늘어남 p.404, 보조): 서울, 신고 기한이 지난 마지막 달 vs 그 전 12개월 평균
    c5 = select(db, """SELECT contract_month AS m, count(*) FILTER (WHERE deal_type = '직거래') * 100.0 / count(*) AS r, count(*) AS n
        FROM deals WHERE region_code LIKE '11%' AND NOT is_cancelled AND contract_month >= to_char(now() - interval '15 months', 'YYYYMM')
        GROUP BY 1 ORDER BY 1""")
    c5 = [r for r in c5 if r["m"] <= last_complete.strftime("%Y%m")]
    if len(c5) >= 13:
        lastr, avg = float(c5[-1]["r"]), sum(float(r["r"]) for r in c5[-13:-1]) / 12
        sig["c5_direct"] = (round(lastr, 1), "늘어남" if lastr > avg * 1.2 else "보통",
                            f"{_ym(c5[-1]['m'])} 서울 매매 {c5[-1]['n']:,}건 중 직거래 {lastr:.1f}%, 그 전 12개월 평균 {avg:.1f}%. "
                            "하락기에 늘어나는 보조 지표(📖 p.404, 🔧 평균의 1.2배 넘으면 늘어남)")
    else:
        sig["c5_direct"] = (None, "데이터 없음", "서울 직거래 비중")
    # D3 역전세 위험 (📖 p.153): 서울 단지·면적 중 지금 전세 < 24개월 전 전세 비율 (complex_metrics, 매일 계산)
    d3 = select(db, "SELECT count(*) FILTER (WHERE reverse_risk) AS r, count(reverse_risk) AS n FROM complex_metrics WHERE apt_seq LIKE '11%'")
    if d3 and d3[0]["n"]:
        share = round(d3[0]["r"] * 100.0 / d3[0]["n"], 1)
        sig["d3_reverse_share"] = (share, "참고", f"서울 단지·면적 {d3[0]['n']:,}개 중 지금 전세가 2년 전 전세보다 낮은 곳 {d3[0]['r']:,}개 ({share}%). "
                                   "대비금 = 전세가의 10%(📖 p.153). 전월세 이력이 서울만 있어 경기·인천은 아직 판정 못 함")
    else:
        sig["d3_reverse_share"] = (None, "데이터 없음", "역전세 위험 단지 비율")
    # G2 기준금리와 서울 아파트값 (동행/역행). 2006년부터 달마다 세고, 최신 달 관계를 신호로
    br, kb = macro(db, "base_rate", 400), macro(db, "apt_kb_seoul", 400)
    rel = [x for x in rate_price_relation(br, kb) if x[0] >= "200601"]
    if rel and br:
        p, lab = rel[-1]
        py = dict(yoy_series(kb)).get(p)
        r = dict(br)
        n = {k: sum(1 for _, x in rel if x == k) for k in ("동행", "역행", "금리 동결")}
        sig["g2_rate_price"] = (r[p], lab, f"{_ym(p)} 기준금리 {r[p]}% (1년 전 {dict(br).get(_shift(p, -12))}%), 서울 아파트 전년비 {py:+.1f}%. "
                                f"2006년 이후 동행 {n['동행']}개월·역행 {n['역행']}개월·금리 동결 {n['금리 동결']}개월. 금리는 집값을 조절하지 않는다(📖 p.48~49)")
    else:
        sig["g2_rate_price"] = (None, "데이터 없음", "기준금리와 서울 아파트값")
    # G3 주담대 금리, G4 가계대출 증가율 (jobs/macro.py, ECOS)
    rate = macro(db, "mortgage_rate", 1)
    sig["g3_mortgage_rate"] = ((rate[-1][1], mortgage_band(rate[-1][1]),
                                f"{_ym(rate[-1][0])} 예금은행 주담대 금리(신규취급액). 3~5% 심리적 한계, 7%면 체감 급변")
                               if rate else (None, "데이터 없음", "예금은행 주담대 금리"))
    for name, key, label in (("household_loans", "g4_household_loans", "예금취급기관 가계대출"),
                             ("housing_loans", "g4_housing_loans", "예금취급기관 주택관련대출")):
        g = loan_growth(macro(db, name, 16))
        sig[key] = ((g.yoy, g.state, f"{_ym(g.period)} {label} 잔액 전년비 {g.yoy:+.2f}%"
                     + (f", 3개월 전 대비 {g.yoy_chg_3m:+.2f}%p (둔화 = 거래 감소 압력)" if g.yoy_chg_3m is not None else ""))
                    if g else (None, "데이터 없음", f"{label} 증가율"))
    # B5 ① 상승 지역 비율 (최신 주)
    for scope, key in (("전국", "b5_up_nat"), ("수도권", "b5_up_cap")):
        r = select(db, f"SELECT week_date::text AS d, n, n_up FROM rone_breadth WHERE stat = 'sale' AND scope = {lit(scope)} "
                       "ORDER BY week_date DESC LIMIT 1")
        sig[key] = ((round(r[0]["n_up"] * 100.0 / r[0]["n"], 1), "참고", f"{scope} 시군구 중 주간 상승 지역 비율 ({r[0]['d']} 주)")
                    if r else (None, "데이터 없음", f"{scope} 상승 지역 비율"))
    # B5 ② 하위 급지 신고가 비중, ③ 상위 급지 대비 비 (📖 "범위의 문제", 립밤 아파트 p.111~114: 다 오르면 과열)
    # 수도권 최근 4주 중개 거래(전고점이 있는 거래) 중 신고가 비율. 하위 = 급지 6~8(12억 미만), 상위 = 1~3(20억+), dong_grade 최신
    yr = today.year
    b5 = select(db, f"""WITH g AS (SELECT region_code, umd_name, grade FROM dong_grade WHERE asof = (SELECT max(asof) FROM dong_grade)),
      r AS (SELECT d.price_10k > d.prev_high_10k AS hi, g.grade, x.build_year, k.households, d.contract_date > {lit(today)}::date - 28 AS cur
        FROM deals d JOIN complexes x USING (apt_seq) JOIN g ON g.region_code = d.region_code AND g.umd_name = x.umd_name
        LEFT JOIN kapt_complexes k ON k.kapt_code = x.kapt_code
        WHERE NOT d.is_cancelled AND d.deal_type = '중개' AND d.prev_high_10k IS NOT NULL AND d.contract_date > {lit(today)}::date - 56)
      SELECT cur, CASE WHEN grade <= 3 THEN 'top' WHEN grade >= 6 THEN 'low' ELSE 'mid' END AS band, count(*) AS n, count(*) FILTER (WHERE hi) AS h,
        count(*) FILTER (WHERE grade >= 6 AND build_year <= {yr - 20} AND coalesce(households, 0) < 300) AS ln,
        count(*) FILTER (WHERE hi AND grade >= 6 AND build_year <= {yr - 20} AND coalesce(households, 0) < 300) AS lh
      FROM r GROUP BY 1, 2""")
    bb = {(r["cur"], r["band"]): r for r in b5}
    pct = lambda h, n: round(h * 100.0 / n, 1) if n else None
    low, top, lowp = bb.get((True, "low")), bb.get((True, "top")), bb.get((False, "low"))
    if low and low["n"] and top and top["n"]:
        lr, tr = pct(low["h"], low["n"]), pct(top["h"], top["n"])
        pr = pct(lowp["h"], lowp["n"]) if lowp else None
        ln = sum(r["ln"] for k, r in bb.items() if k[0])
        lh = sum(r["lh"] for k, r in bb.items() if k[0])
        sp = round(lr / tr, 2) if tr else None
        trend = "" if pr is None else f", 그 전 4주 {pr}% ({'증가' if lr > pr else '감소' if lr < pr else '유지'})"
        sig["b5_low_highs"] = (lr, b5_state(lr, sp),
                               f"수도권 최근 4주 하위 급지(6~8급, 12억 미만) 거래 {low['n']:,}건 중 신고가 {lr}%{trend}"
                               + (f". 그중 구축(20년+)·소단지(300세대 미만) {ln:,}건은 {pct(lh, ln)}%" if ln else "")
                               + f". 약한 아파트까지 신고가면 과열(📖 p.111~114). 🔧 {B5_WATCH:.0f}% 이상 주의, {B5_HOT:.0f}% 이상 + 상위 대비 {B5_SPREAD}배 이상 과열"
                               " (2021 불장 30~41%, 2023~25년 2~3%)")
        sig["b5_spread"] = (sp, "데이터 없음" if sp is None else "충족" if sp >= B5_SPREAD else "미충족",
                            f"하위 급지 신고가 비중 {lr}% ÷ 상위 급지(1~3급, 20억+) {tr}% (상위 {top['n']:,}건). 1에 가까울수록 상승이 아래까지 번진 것"
                            f" (🔧 {B5_SPREAD}배, 2021 불장 0.62~0.79). 하위 비중이 낮을 때는 비가 흔들려 과열 판정은 ②와 함께 본다")
    else:
        sig["b5_low_highs"] = (None, "데이터 없음", "하위 급지 신고가 비중")
        sig["b5_spread"] = (None, "데이터 없음", "상위 대비 하위 급지 신고가 비중")
    # 반등 신호: 매매수급지수
    sup, sale = series(db, "sale_supply", 6), series(db, "sale", 6)
    for cid, nm in ((SEOUL, "seoul"), (CAPITAL, "sudo")):
        sd = dict(sale.get(cid, []))
        pts = [(d, x) for d, x in sup.get(cid, []) if d in sd]   # 같은 주끼리
        v, s = [x for _, x in pts], [sd[d] for d, _ in pts]
        if len(v) < 2:
            sig[f"supply_{nm}"] = (None, "데이터 없음", "매매수급지수")
            continue
        up, st = rebound_state(v, s)
        sig[f"supply_{nm}"] = (round(v[-1], 1), st,
                               f"매매수급지수 {v[-1]:.1f} (100 초과 = 매수 우위), {up}주 연속 상승 (기준 {SUPPLY_WEEKS}주)"
                               + (". 매매지수가 13주 전보다 낮지 않아 '전환'을 볼 때가 아님" if st == "하락 중 아님" else
                                  ". 하락 중 4주 연속 상승: 2012년 이후 26주 뒤 평균 수도권 +0.2%(하락 중 아무 주 -1.5%), 2022-04처럼 틀린 적도 있음"))

    vals = ", ".join("(" + ", ".join(lit(x) for x in (k, asof, val, state, detail)) + ")" for k, (val, state, detail) in sig.items())
    stmts.append("INSERT INTO market_signals (key, asof, value, state, detail) VALUES " + vals +
                 " ON CONFLICT (key) DO UPDATE SET asof = EXCLUDED.asof, value = EXCLUDED.value, state = EXCLUDED.state, detail = EXCLUDED.detail;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    return sig


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        sig = run(connect(a.db))
    except DbError as e:
        print(f"[market] 실패: {e}", file=sys.stderr)
        return 1
    for k, (v, s, d) in sig.items():
        print(f"  {k:16} {str(v):>8}  {s:10}  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
