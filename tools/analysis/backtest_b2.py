"""B2 전고점 회복 패턴 기준선 백테스트 (2026-10-19, docs/insights/backtests.md).
판정 시점 A(2024-06, 2024-12)에 단지 84㎡(84·85형)의 회복률 (C−T)/(P−T) 로 패턴을 나누고, A → 2026-08 기준 시세 변화를
같은 시군구 단지 중앙값과 비교한다(시장 전체 흐름을 뺀 초과 상승).
기준 시세 = 그 달 포함 3개월 1층 제외 중개·비해제 거래 중앙값(🔧 2건+), P = 2021-01~2022-06 최고, T = 2022-07~2023-06 최저.
    python tools/analysis/backtest_b2.py <작업 폴더>   # 작업 폴더/arch 에 deals_YYYYMM.csv.gz(2020-01~DB 시작 전), 결과는 b2_monthly.pkl 캐시
"""
import collections
import math
import os
import pickle
import sys
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from collector.archive import asset_name, decode, open_store
from collector.db import connect, select

W = sys.argv[1]
cache = os.path.join(W, "b2_monthly.pkl")
if os.path.exists(cache):
    by = pickle.load(open(cache, "rb"))
else:
    db = connect("api")
    first = select(db, "SELECT min(contract_month) AS m FROM deals")[0]["m"]
    store = open_store("dir:" + os.path.join(W, "arch"))
    by = collections.defaultdict(lambda: collections.defaultdict(list))   # apt_seq → 월 → 가격들
    y, m = 2020, 1
    while f"{y}{m:02d}" < first:
        for r in decode(store.get(asset_name("deal", f"{y}{m:02d}"))):
            if r["is_cancelled"] in ("1", "True", "true") or r["deal_type"] != "중개" or r.get("floor") == "1" or not r["area_m2"]:
                continue
            if math.floor(float(r["area_m2"])) in (84, 85):
                by[r["apt_seq"]][r["contract_month"]].append(int(r["price_10k"]))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    for r in select(db, f"""SELECT apt_seq, contract_month AS m, price_10k AS p FROM deals WHERE NOT is_cancelled AND deal_type = '중개'
                           AND floor IS DISTINCT FROM 1 AND area_group IN (84, 85) AND contract_month >= '{first}'"""):
        by[r["apt_seq"]][r["m"]].append(int(r["p"]))
    by = {a: dict(v) for a, v in by.items()}
    pickle.dump(by, open(cache, "wb"))


def months(a, b):
    y, m = int(a[:4]), int(a[4:])
    out = []
    while f"{y}{m:02d}" <= b:
        out.append(f"{y}{m:02d}")
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


ALL = months("202001", "202608")


def ref(s, mth):
    i = ALL.index(mth)
    win = sum((s.get(x, []) for x in ALL[max(0, i - 2):i + 1]), [])
    return median(win) if len(win) >= 2 else None


def run(asof, end="202608", cut=60.0):
    rows = []
    for a, s in by.items():
        refs = {m: ref(s, m) for m in months("202101", "202306")}
        pk = [v for m, v in refs.items() if m <= "202206" and v]
        tr = [v for m, v in refs.items() if m >= "202207" and v]
        c, f = ref(s, asof), ref(s, end)
        if not pk or not tr or not c or not f:
            continue
        P, T = max(pk), min(tr)
        if P <= T:
            continue
        rate = (c - T) / (P - T) * 100
        pat = "신고가 돌파" if c >= P else ("순조로운" if rate >= cut else "회복 지연")
        rows.append((a, a[:5], pat, rate, f / c - 1, c <= T * 1.03))
    med = {rc: median([r[4] for r in rows if r[1] == rc]) for rc in {r[1] for r in rows}}
    return [(a, rc, pat, rate, fwd - med[rc], nob) for a, rc, pat, rate, fwd, nob in rows]


for asof in ("202406", "202412"):
    print(f"=== 판정 {asof} → 2026-08 (같은 구 중앙값 대비 초과 상승)")
    rs = run(asof)
    for pat in ("신고가 돌파", "순조로운", "회복 지연"):
        v = sorted(r[4] for r in rs if r[2] == pat)
        if v:
            print(f"  {pat}: {len(v):,}곳 평균 {sum(v)/len(v)*100:+.2f}%p 중앙값 {v[len(v)//2]*100:+.2f}%p 구 중앙값보다 더 오른 비율 {sum(1 for x in v if x > 0)*100/len(v):.0f}%")
    nob = sorted(r[4] for r in rs if r[5])
    print(f"  (경고) 2023년 초 대비 반등 없음(C ≤ T×1.03): {len(nob):,}곳 평균 {sum(nob)/max(1,len(nob))*100:+.2f}%p 더 오른 비율 {sum(1 for x in nob if x > 0)*100/max(1,len(nob)):.0f}%")
    print("  회복률 구간별:")
    for lo, hi in ((-999, 0), (0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 9999)):
        v = sorted(r[4] for r in rs if lo <= r[3] < hi)
        if v:
            print(f"    {lo if lo > -999 else '<'}~{hi if hi < 9999 else ''}%: {len(v):,}곳 평균 {sum(v)/len(v)*100:+.2f}%p 중앙값 {v[len(v)//2]*100:+.2f}%p 더 오른 비율 {sum(1 for x in v if x > 0)*100/len(v):.0f}%")
