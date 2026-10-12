"""시장 국면·체크리스트 신호 계산 (collector/market.py, 0011). rone weekly 뒤에 돈다.

    python -m jobs.market

region_phase: 지역별 B1 국면·B3 낙폭 (매매·전세)
market_signals: 홈 체크리스트 (서울·수도권 국면, B4 하락 분류 조건, B5 상승 지역 비율, 매매수급지수)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from collector.db import Db, DbError, connect, lit, select
from collector.market import (DOWN_RATIO, JEONSE_WEEKS, SUPPLY_WEEKS, UNEMP_JUMP, b4, monthly, phase, run_length, unemployment)

SEOUL, CAPITAL = 50008, 50002


def series(db: Db, stat: str, months: int = 30) -> dict[int, list[tuple[date, float]]]:
    rows = select(db, f"SELECT cls_id, week_date::text AS d, value FROM rone_weekly WHERE stat = {lit(stat)} "
                      f"AND week_date >= (SELECT max(week_date) FROM rone_weekly WHERE stat = {lit(stat)}) - {months * 31} "
                      "ORDER BY cls_id, week_date")
    out: dict[int, list[tuple[date, float]]] = {}
    for r in rows:
        out.setdefault(r["cls_id"], []).append((date.fromisoformat(r["d"]), float(r["value"])))
    return out


def run(db: Db) -> dict[str, tuple]:
    stmts = ["BEGIN;", "DELETE FROM region_phase;"]
    phases: dict[tuple[str, int], object] = {}
    asof = None
    for stat in ("sale", "jeonse"):
        ser = series(db, stat)
        vals = []
        for cid, pts in ser.items():
            ph = phase(monthly(pts))
            phases[(stat, cid)] = ph
            asof = max(asof or pts[-1][0], pts[-1][0])
            vals.append("(" + ", ".join(lit(v) for v in (stat, cid, pts[-1][0], ph.chg_12m, ph.up_months, ph.down_months,
                                                        ph.last3, ph.phase, ph.drawdown)) + ")")
        if vals:
            stmts.append("INSERT INTO region_phase (stat, cls_id, asof, chg_12m, up_months, down_months, last3, phase, drawdown) VALUES "
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
    um = unemployment([(r["period"], float(r["value"])) for r in select(
        db, "SELECT period, value FROM macro_monthly WHERE series = 'unemployment_sa' ORDER BY period DESC LIMIT 4")][::-1])
    met, known, cls = b4(ratio4, jdown, um.b4_met if um else None)
    sudo_phase = getattr(phases.get(("sale", CAPITAL)), "phase", None)
    falling = sudo_phase in ("하락장", "일시 조정")
    sig["b4_down_ratio"] = (ratio4, "데이터 없음" if ratio4 is None else "충족" if ratio4 >= DOWN_RATIO else "미충족",
                            f"전국 시군구 중 주간 하락 지역 비율 최근 4주 평균 (기준 {DOWN_RATIO:.0f}%)")
    sig["b4_jeonse_8w"] = (jdown, "데이터 없음" if jdown is None else "충족" if jdown >= JEONSE_WEEKS else "미충족",
                           f"수도권 전세지수 연속 하락 주 (기준 {JEONSE_WEEKS}주)")
    if um:
        chg = f"{um.chg_3m:+.1f}%p" if um.chg_3m is not None else "비교 불가"
        sig["b4_unemployment"] = (um.rate, "충족" if um.b4_met else "미충족",
                                  f"{um.period[:4]}.{um.period[4:]} 계절조정 실업률 {um.rate}%, 3개월 전 대비 {chg} (기준 4% 또는 +{UNEMP_JUMP}%p)")
        sig["g5_unemployment"] = (um.rate, um.band, f"{um.period[:4]}.{um.period[4:]} 계절조정 실업률. 4% 미만 안정, 4~6% 경기침체, 6% 이상 경제 위기")
    else:
        sig["b4_unemployment"] = (None, "데이터 없음", "실업률 4% 이상 또는 3개월 +0.5%p (macro_monthly 비어 있음)")
        sig["g5_unemployment"] = (None, "데이터 없음", "계절조정 실업률")
    sig["b4_class"] = (met, cls if falling else "해당 없음",
                       f"수도권 국면 {sudo_phase}. 하락 국면일 때만 판정. 조건 {met}/{known}개 충족 (판단 가능 {known}/3)")
    # B5 ① 상승 지역 비율 (최신 주)
    for scope, key in (("전국", "b5_up_nat"), ("수도권", "b5_up_cap")):
        r = select(db, f"SELECT week_date::text AS d, n, n_up FROM rone_breadth WHERE stat = 'sale' AND scope = {lit(scope)} "
                       "ORDER BY week_date DESC LIMIT 1")
        sig[key] = ((round(r[0]["n_up"] * 100.0 / r[0]["n"], 1), "참고", f"{scope} 시군구 중 주간 상승 지역 비율 ({r[0]['d']} 주)")
                    if r else (None, "데이터 없음", f"{scope} 상승 지역 비율"))
    # 반등 신호: 매매수급지수
    sup = series(db, "sale_supply", 6)
    for cid, nm in ((SEOUL, "seoul"), (CAPITAL, "sudo")):
        v = [x for _, x in sup.get(cid, [])]
        if len(v) < 2:
            sig[f"supply_{nm}"] = (None, "데이터 없음", "매매수급지수")
            continue
        up = run_length(v, +1)
        sig[f"supply_{nm}"] = (round(v[-1], 1), "상승 전환" if up >= SUPPLY_WEEKS else "아님",
                               f"매매수급지수 {v[-1]:.1f} (100 초과 = 매수 우위), {up}주 연속 상승 (기준 {SUPPLY_WEEKS}주)")

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
