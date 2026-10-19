"""B1 국면 라벨 단지 단위 백테스트 (2026-10-20, docs/insights/backtests.md).
지역(R-ONE 지수) 백테스트(backtest_b1.py)와 같은 규칙을 단지 84㎡(84·85형) 월별 기준 시세에 대 본다.
기준 시세 = 그 달 포함 3개월 1층 제외 중개·비해제 거래 중앙값(sql/metrics.sql ref13 과 같음, 창에 거래 min_n 건 이상).
라벨 뒤 6·12개월 기준 시세 변화를 (1) 오른·떨어진 비율 (2) 같은 시군구 단지 중앙값 대비 초과로 본다.
    python tools/analysis/backtest_b1_complex.py <작업 폴더>   # 작업 폴더/b2_monthly.pkl (backtest_b2.py 가 만든 캐시: 단지 → 월 → 가격들)
"""
import collections
import os
import pickle
import sys
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from collector import market as M

W = sys.argv[1]
LAST = "202608"     # 이 뒤는 신고가 덜 들어와 뺀다
by = pickle.load(open(os.path.join(W, "b2_monthly.pkl"), "rb"))


def months(a, b):
    y, m = int(a[:4]), int(a[4:])
    out = []
    while f"{y}{m:02d}" <= b:
        out.append(f"{y}{m:02d}")
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


ALL = months("202001", LAST)
IDX = {m: i for i, m in enumerate(ALL)}


def refs(min_n):
    """단지 → 월별 기준 시세 리스트(ALL 순서, 없으면 None)."""
    out = {}
    for a, mm in by.items():
        v = []
        for i in range(len(ALL)):
            ps = [p for k in ALL[max(0, i - 2):i + 1] for p in mm.get(k, ())]
            v.append(median(ps) if len(ps) >= min_n else None)
        if sum(x is not None for x in v) >= 13:
            out[a] = v
    return out


def labels(ref):
    """(단지, 월 i) → 국면. 13개월 모두 기준 시세가 있을 때만(metrics 와 같음)."""
    out = {}
    for a, v in ref.items():
        for i in range(12, len(v)):
            w = v[i - 12:i + 1]
            if None in w:
                continue
            out[(a, i)] = M.phase(list(zip(ALL[i - 12:i + 1], w))).phase
    return out


def run(ref, lab, h, skip=0):
    """skip: 라벨 시점 기준 시세와 거래가 겹치지 않게 skip 개월 뒤부터 잰다(3 이면 창이 안 겹침 — 잡음 때문에 생기는 되돌림을 뺀다)."""
    fwd = {}
    for (a, i), p in lab.items():
        j = i + skip
        if j + h < len(ALL) and ref[a][j] is not None and ref[a][j + h] is not None:
            fwd[(a, i)] = ref[a][j + h] / ref[a][j] - 1
    # 같은 시군구·같은 시점 중앙값 (라벨이 있는 단지끼리)
    grp = collections.defaultdict(list)
    for (a, i), r in fwd.items():
        grp[(a[:5], i)].append(r)
    med = {k: median(v) for k, v in grp.items() if len(v) >= 5}
    st = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0, 0])   # n, up, down, sum, n_ex, beat
    for (a, i), r in fwd.items():
        s = st[lab[(a, i)]]
        s[0] += 1; s[1] += r > 0; s[2] += r < 0; s[3] += r
        m = med.get((a[:5], i))
        if m is not None:
            s[4] += 1; s[5] += r > m
    base = [sum(s[k] for s in st.values()) for k in range(6)]
    return st, base


for min_n in (1, 2, 3):
    ref = refs(min_n)
    print(f"\n### 3개월 창 거래 {min_n}건 이상 — 단지 {len(ref):,}곳")
    for up_min, consist in ((3.0, 8), (2.0, 8), (5.0, 8), (3.0, 7), (3.0, 9)):
        if min_n != 1 and (up_min, consist) != (3.0, 8):
            continue
        M.UP_MIN, M.CONSIST = up_min, consist
        lab = labels(ref)
        for h in (6, 12):
            st, b = run(ref, lab, h)
            tot = b[0]
            print(f"±{up_min}% {consist}개월 · {h}개월 뒤 | 평소 오름 {b[1] * 100 / tot:.1f}% 떨어짐 {b[2] * 100 / tot:.1f}% (n {tot:,})")
            for p in ("상승장", "하락장", "보합장", "일시 반등", "일시 조정", "추세 불명확"):
                s = st.get(p)
                if not s or not s[0]:
                    continue
                print(f"   {p:6} {s[0] * 100 / tot:5.1f}% | 오름 {s[1] * 100 / s[0]:5.1f}% 떨어짐 {s[2] * 100 / s[0]:5.1f}% 평균 {s[3] * 100 / s[0]:+6.2f}%"
                      f" | 구 중앙값보다 더 오름 {s[5] * 100 / s[4] if s[4] else float('nan'):5.1f}% (n {s[4]:,})")

# 잡음 확인: 창이 안 겹치게 3개월 뒤부터 잰 결과 (±3%, 8개월, 거래 1건+)
M.UP_MIN, M.CONSIST = 3.0, 8
ref = refs(1)
lab = labels(ref)
for h in (6, 12):
    st, b = run(ref, lab, h, skip=3)
    tot = b[0]
    print(f"\n[3개월 뒤부터] {h}개월 | 평소 오름 {b[1] * 100 / tot:.1f}% 떨어짐 {b[2] * 100 / tot:.1f}% (n {tot:,})")
    for p in ("상승장", "하락장", "보합장", "일시 반등", "일시 조정", "추세 불명확"):
        s = st.get(p)
        if s and s[0]:
            print(f"   {p:6} 오름 {s[1] * 100 / s[0]:5.1f}% 떨어짐 {s[2] * 100 / s[0]:5.1f}% 평균 {s[3] * 100 / s[0]:+6.2f}% | 구 중앙값보다 더 오름 {s[5] * 100 / s[4]:5.1f}% (n {s[4]:,})")

# B6 상대강도: 12개월 변화 − 같은 구 중앙값, 5분위 → 그 뒤(3개월 건너뛰고) 12개월 같은 구 대비 초과
print("\nB6 상대강도 5분위 (낮음 → 높음), 3개월 건너뛰고 12개월 뒤 같은 구 중앙값보다 더 오른 비율 / 초과 평균")
chg = {}
for (a, i), p in lab.items():
    chg[(a, i)] = ref[a][i] / ref[a][i - 12] - 1
g = collections.defaultdict(list)
for (a, i), c in chg.items():
    g[(a[:5], i)].append(c)
gm = {k: median(v) for k, v in g.items() if len(v) >= 5}
rs = {k: c - gm[(k[0][:5], k[1])] for k, c in chg.items() if (k[0][:5], k[1]) in gm}
fw = {}
for (a, i) in rs:
    j = i + 3
    if j + 12 < len(ALL) and ref[a][j] is not None and ref[a][j + 12] is not None:
        fw[(a, i)] = ref[a][j + 12] / ref[a][j] - 1
g2 = collections.defaultdict(list)
for (a, i), r in fw.items():
    g2[(a[:5], i)].append(r)
fm = {k: median(v) for k, v in g2.items() if len(v) >= 5}
xs = sorted((rs[k], fw[k] - fm[(k[0][:5], k[1])]) for k in fw if (k[0][:5], k[1]) in fm)
q = len(xs) // 5
for n in range(5):
    part = xs[n * q:(n + 1) * q if n < 4 else len(xs)]
    print(f"   {n + 1}분위 상대강도 {part[0][0] * 100:+.1f}~{part[-1][0] * 100:+.1f}%p | 더 오름 {sum(e > 0 for _, e in part) * 100 / len(part):.1f}% 초과 평균 {sum(e for _, e in part) * 100 / len(part):+.2f}%p (n {len(part):,})")

# 연도별: 상승장·하락장 라벨 뒤 12개월 (기준 ±3%, 8개월, 거래 1건+)
M.UP_MIN, M.CONSIST = 3.0, 8
ref = refs(1)
lab = labels(ref)
yr = collections.defaultdict(lambda: [0, 0])
for (a, i), p in lab.items():
    if p in ("상승장", "하락장") and i + 12 < len(ALL) and ref[a][i + 12] is not None:
        r = ref[a][i + 12] / ref[a][i] - 1
        k = (ALL[i][:4], p)
        yr[k][0] += 1; yr[k][1] += (r > 0) if p == "상승장" else (r < 0)
print("\n연도별 12개월 뒤 적중(상승장=오름, 하락장=떨어짐):", {f"{y} {p}": f"{h * 100 // n}% ({n})" for (y, p), (n, h) in sorted(yr.items())})
