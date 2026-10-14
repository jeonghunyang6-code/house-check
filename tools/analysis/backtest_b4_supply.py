"""B4 ②(수도권 전세 N주 연속 하락)·반등 신호(매매수급지수 N주 연속 상승) 백테스트 (2026-10-14).

R-ONE 주간 지수 2012년~ 전체(rone_weekly)로 신호가 켜진 주를 찾고, 그 뒤 매매지수가 어떻게 움직였는지 본다.
신호는 연속 구간마다 처음 기준에 닿은 주 한 번만 센다. 실행: python tools/analysis/backtest_b4_supply.py
"""
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.db import connect, select

SEOUL, CAPITAL = 50008, 50002
db = connect("api")
S = {}
for r in select(db, "SELECT stat, cls_id, week_date::text d, value FROM rone_weekly WHERE cls_id IN (50008, 50002) "
                    "AND stat IN ('sale','jeonse','sale_supply') ORDER BY week_date"):
    S.setdefault((r["stat"], r["cls_id"]), []).append((date.fromisoformat(r["d"]), float(r["value"])))


def runs(pts, direction):
    """주마다 끝에서부터 같은 방향 연속 주 수."""
    out, n = [], 0
    for i, (d, v) in enumerate(pts):
        n = n + 1 if i and (v - pts[i - 1][1]) * direction > 0 else 0
        out.append((d, n))
    return out


def fwd(pts, d, weeks):
    """d 주부터 weeks 주 뒤 매매지수 변화 %."""
    idx = {x: i for i, (x, _) in enumerate(pts)}
    i = idx.get(d)
    if i is None or i + weeks >= len(pts):
        return None
    return round((pts[i + weeks][1] / pts[i][1] - 1) * 100, 2)


def onsets(rl, k):
    return [d for (d, n), (_, p) in zip(rl, [(None, 0)] + rl[:-1]) if n >= k and p < k]


def report(title, sig_pts, sale_pts, direction, ks, horizons=(13, 26, 52)):
    print(f"\n## {title}")
    rl = runs(sig_pts, direction)
    longest = max(rl, key=lambda x: x[1])
    print(f"기간 {sig_pts[0][0]}~{sig_pts[-1][0]}, 최장 연속 {longest[1]}주 ({longest[0]} 주까지)")
    base = {h: [fwd(sale_pts, d, h) for d, _ in sale_pts] for h in horizons}
    print("기준선(아무 주나): " + ", ".join(
        f"{h}주 뒤 평균 {sum(x for x in base[h] if x is not None) / len([x for x in base[h] if x is not None]):+.2f}%" for h in horizons))
    for k in ks:
        os_ = onsets(rl, k)
        print(f"\n{k}주 기준: 신호 {len(os_)}번")
        for d in os_:
            print(f"  {d}  " + "  ".join(f"{h}주 뒤 {fwd(sale_pts, d, h) if fwd(sale_pts, d, h) is not None else '–':>6}" for h in horizons))


for cid, nm in ((CAPITAL, "수도권"), (SEOUL, "서울")):
    report(f"B4 ② {nm} 전세지수 연속 하락 → 매매지수", S[("jeonse", cid)], S[("sale", cid)], -1, (4, 8, 12))


def falling(sale_pts, d, weeks=13):
    """d 주 기준 매매지수가 weeks 주 전보다 낮으면 하락 중."""
    idx = {x: i for i, (x, _) in enumerate(sale_pts)}
    i = idx.get(d)
    return i is not None and i >= weeks and sale_pts[i][1] < sale_pts[i - weeks][1]


def summary(title, sig_pts, sale_pts, ks, horizons=(13, 26, 52)):
    """반등 신호는 '전환'이므로 하락 중(매매지수 13주 전보다 낮음)일 때 켜진 것만 센다. 비교 기준 = 하락 중인 아무 주."""
    print(f"\n## {title} (하락 중일 때만)")
    base = [d for d, _ in sale_pts if falling(sale_pts, d)]
    def stat(ds, h):
        xs = [x for x in (fwd(sale_pts, d, h) for d in ds) if x is not None]
        return f"{h}주 뒤 평균 {sum(xs) / len(xs):+.2f}% 상승 {sum(x > 0 for x in xs)}/{len(xs)}" if xs else f"{h}주 뒤 –"
    print(f"기준선(하락 중 아무 주 {len(base)}개): " + ", ".join(stat(base, h) for h in horizons))
    rl = runs(sig_pts, +1)
    for k in ks:
        os_ = [d for d in onsets(rl, k) if falling(sale_pts, d)]
        print(f"{k}주 기준 신호 {len(os_)}번: " + ", ".join(stat(os_, h) for h in horizons))
        print("   " + " ".join(str(d) for d in os_))


for cid, nm in ((CAPITAL, "수도권"), (SEOUL, "서울")):
    summary(f"반등 신호 {nm} 매매수급지수 연속 상승 → 매매지수", S[("sale_supply", cid)], S[("sale", cid)], (3, 4, 6, 8))
