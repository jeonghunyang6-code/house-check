"""E6 격차 위치 기준선 백테스트 (2026-10-19, docs/insights/backtests.md). 84㎡ 분기 중앙가 2020Q1~2026Q3, 10km 안 1.5~2.5배 쌍,
그 분기까지의 격차 위치(과거 최대 20분기 중 백분위)별로 H 분기 뒤 배율 변화.
    python tools/analysis/backtest_e6.py <작업 폴더> <H>   # 작업 폴더/arch 에 deals_YYYYMM.csv.gz 보관 파일, 결과는 e6_series.pkl 로 캐시
"""
import sys, json, math, collections, pickle, os
sys.path.insert(0, '/home/user/house-check')
from collector.db import connect, select
from collector.archive import open_store
from collector.gap import dist_m
from jobs.gap import series
S = sys.argv[1]
qs = [f"{y}Q{q}" for y in range(2020, 2027) for q in (1, 2, 3, 4)][:27]   # 2020Q1 ~ 2026Q3
cache = S + '/e6_series.pkl'
if os.path.exists(cache):
    ser, coords = pickle.load(open(cache, 'rb'))
else:
    db = connect('api')
    ser = series(db, open_store('dir:' + S + '/arch'), qs)
    coords = {r["apt_seq"]: (float(r["lat"]), float(r["lng"])) for r in select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")}
    pickle.dump((ser, coords), open(cache, 'wb'))
ok = [a for a, s in ser.items() if sum(1 for q in qs if q in s) >= 16 and a in coords]
print('complexes', len(ok))
grid = collections.defaultdict(list)
for a in ok:
    la, lo = coords[a]; grid[(int(la / 0.1), int(lo / 0.13))].append(a)
res = collections.defaultdict(list)
H = int(sys.argv[2]) if len(sys.argv) > 2 else 4
for a in ok:
    la, lo = coords[a]; ga, go = int(la / 0.1), int(lo / 0.13)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for b in grid[(ga + dx, go + dy)]:
                if b == a or dist_m(la, lo, *coords[b]) > 10000:
                    continue
                sa, sb = ser[a], ser[b]
                joint = [q for q in qs if q in sa and q in sb]
                idx = {q: i for i, q in enumerate(qs)}
                for i in range(11, len(qs) - H):
                    q, qf = qs[i], qs[i + H]
                    if q not in sa or q not in sb or qf not in sa or qf not in sb:
                        continue
                    r = sb[q] / sa[q]
                    if not 1.5 <= r <= 2.5:
                        continue
                    past = [sb[x] - sa[x] for x in joint if idx[x] <= i][-20:]
                    if len(past) < 8:
                        continue
                    g = sb[q] - sa[q]
                    pct = sum(1 for v in past if v <= g) * 100 / len(past)
                    fr = (sb[qf] / sa[qf]) / r - 1
                    res['≤10' if pct <= 10 else '10~20' if pct <= 20 else '20~30' if pct <= 30 else '30~50' if pct <= 50 else '50~80' if pct <= 80 else '>80'].append(fr)
for k in ('≤10', '10~20', '20~30', '30~50', '50~80', '>80'):
    v = res[k]
    if v:
        v.sort()
        print(f"격차 위치 {k}: n={len(v):,} {H}분기 뒤 배율 변화 평균 {sum(v)/len(v)*100:+.2f}% 중앙값 {v[len(v)//2]*100:+.2f}% 배율 커진 비율 {sum(1 for x in v if x > 0)*100/len(v):.1f}%")
