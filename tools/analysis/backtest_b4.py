"""B4 ① 하락 지역 비율 기준선 백테스트 (2026-10-19, docs/insights/backtests.md). 저장된 R-ONE 은 수도권 말단 시군구뿐이라 전국 대신 수도권 78곳으로 근사.
    python tools/analysis/backtest_b4.py <작업 폴더>   # rone_all.json 필요
"""
import json, sys, collections
from datetime import date
S = sys.argv[1]
rows = [r for r in json.load(open(S + '/rone_all.json')) if r['stat'] == 'sale']
by = collections.defaultdict(dict)
names = {}
for r in rows:
    by[r['cls_id']][r['d']] = r['v']; names[r['cls_id']] = r['full_name']
parents = {n.rsplit('>', 1)[0] for n in names.values() if '>' in n}
AGG = {"전국", "수도권", "지방권", "4대광역시", "5대광역시", "7개도", "8개도"}
leaves = [c for c, n in names.items() if n not in parents and n not in AGG and (n.startswith('서울') or n.startswith('경기') or n.startswith('인천'))]
weeks = sorted({d for c in leaves for d in by[c]})
ratio = []
for a, b in zip(weeks, weeks[1:]):
    ups = [c for c in leaves if a in by[c] and b in by[c]]
    if len(ups) < 20: continue
    ratio.append((b, sum(by[c][b] < by[c][a] for c in ups) * 100 / len(ups)))
sudo = next(c for c, n in names.items() if n == '수도권')
sw = sorted(by[sudo].items())
idx = {d: i for i, (d, _) in enumerate(sw)}
print('수도권 말단 지역', len(leaves), '주', len(ratio))
r4 = [(ratio[i][0], sum(x for _, x in ratio[i-3:i+1]) / 4) for i in range(3, len(ratio))]
for th in (50, 60, 70, 80):
    for H in (26, 52):
        hit = [];
        for d, v in r4:
            if v >= th and d in idx and idx[d] + H < len(sw):
                hit.append(sw[idx[d] + H][1] / sw[idx[d]][1] - 1)
        base = [sw[i + H][1] / sw[i][1] - 1 for i in range(len(sw) - H)]
        if hit:
            print(f'하락 비율 4주 평균 ≥{th}%: {len(hit)}주 켜짐, {H}주 뒤 수도권 매매 평균 {sum(hit)/len(hit)*100:+.2f}%, 더 떨어진 비율 {sum(1 for x in hit if x<0)*100/len(hit):.0f}%  (평소 떨어진 비율 {sum(1 for x in base if x<0)*100/len(base):.0f}%)')
# 켜진 구간(연속)과 시작 주
on = False
for d, v in r4:
    if v >= 70 and not on: print('  70% 켜짐 시작', d); on = True
    elif v < 70 and on: on = False
