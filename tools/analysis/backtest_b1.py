"""B1 국면 기준선 백테스트 (2026-10-19, docs/insights/backtests.md). R-ONE 주간 매매지수 123개 지역 2012~ → 월별, 국면 라벨 뒤 6·12개월 변화.
    python tools/analysis/backtest_b1.py <작업 폴더>   # 작업 폴더에 rone_all.json (rone_weekly 덤프)이 있어야 한다
"""
import json, sys, collections
sys.path.insert(0, '/home/user/house-check')
from datetime import date
from collector import market as M
S = sys.argv[1]
rows = json.load(open(S + '/rone_all.json'))
ser = collections.defaultdict(list)
for r in rows:
    if r['stat'] == 'sale':
        ser[r['cls_id']].append((date.fromisoformat(r['d']), r['v']))
monthly = {c: M.monthly(v) for c, v in ser.items()}

def run(up_min, consist, horizon):
    M.UP_MIN, M.CONSIST = up_min, consist
    stat = collections.Counter()
    for c, ms in monthly.items():
        for i in range(13, len(ms) - horizon):
            p = M.phase(ms[:i + 1]).phase
            fwd = ms[i + horizon][1] / ms[i][1] - 1
            stat[(p, 'n')] += 1
            stat[(p, 'up')] += fwd > 0
            stat[(p, 'down')] += fwd < 0
            stat[(p, 'sum')] += fwd
    tot = sum(v for (p, k), v in stat.items() if k == 'n')
    out = {}
    for p in ('상승장', '하락장', '보합장', '일시 반등', '일시 조정', '추세 불명확'):
        n = stat[(p, 'n')]
        if n:
            hit = stat[(p, 'up')] / n if p in ('상승장', '일시 반등') else stat[(p, 'down')] / n if p in ('하락장', '일시 조정') else None
            out[p] = (round(n * 100 / tot, 1), None if hit is None else round(hit * 100, 1), round(stat[(p, 'sum')] / n * 100, 2))
    return out

for h in (6, 12):
    print(f'=== 앞으로 {h}개월')
    for up_min in (2.0, 3.0, 5.0):
        for consist in (7, 8, 9):
            o = run(up_min, consist, h)
            print(f'±{up_min}% {consist}개월 |', ' | '.join(f"{p} {v[0]}% 적중 {v[1]} 평균 {v[2]:+}%" for p, v in o.items() if p in ('상승장', '하락장', '보합장')))

print('=== 기준(아무 달이나)')
for h in (6, 12):
    n = up = 0
    for c, ms in monthly.items():
        for i in range(13, len(ms) - h):
            n += 1; up += ms[i + h][1] > ms[i][1]
    print(h, '개월 뒤 오른 비율', round(up * 100 / n, 1), 'n', n)
# 하락장 라벨 뒤 12개월: 2022년대 vs 그 밖
M.UP_MIN, M.CONSIST = 3.0, 8
by = collections.Counter()
for c, ms in monthly.items():
    for i in range(13, len(ms) - 12):
        if M.phase(ms[:i + 1]).phase == '하락장':
            y = ms[i][0][:4]
            by[(y, 'n')] += 1; by[(y, 'down')] += ms[i + 12][1] < ms[i][1]
print('하락장 라벨 연도별 12개월 뒤 계속 하락 비율:', {y: f"{by[(y,'down')]*100//by[(y,'n')]}% ({by[(y,'n')]})" for y in sorted({k[0] for k in by})})
