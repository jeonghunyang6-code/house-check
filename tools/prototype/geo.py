"""행정동 경계(vuski/admdongkor ver20260701) → 수도권 시군구 SVG 경로. 공유 변을 지워 시군구 외곽선만 남기고 단순화한다.

    python tools/prototype/geo.py <HangJeongDong_ver20260701.geojson>   # → data/geo/sudogwon_sgg_20260701.json
출처 표기는 data/geo/ATTRIBUTION.md.
"""
import json, math, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from collector.regions import REGIONS
g = json.load(open(sys.argv[1]))
R = lambda p: (round(p[0], 5), round(p[1], 5))
seg = collections.defaultdict(collections.Counter)
for f in g['features']:
    p = f['properties']
    if p['sgg'] not in REGIONS: continue
    geom = f['geometry']; polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    for poly in polys:
        for ring in poly:
            pts = [R(q) for q in ring]
            for a, b in zip(pts, pts[1:]):
                if a != b: seg[p['sgg']][tuple(sorted((a, b)))] += 1
LAT0 = 37.5; K = math.cos(math.radians(LAT0))
def proj(pt): return ((pt[0] - 126.0) * K * 1000, (38.4 - pt[1]) * 1000)
def dp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    i, dmax = 0, 0
    for k in range(1, len(pts) - 1):
        d = abs(dy * (pts[k][0] - a[0]) - dx * (pts[k][1] - a[1])) / L
        if d > dmax: i, dmax = k, d
    return dp(pts[:i + 1], eps)[:-1] + dp(pts[i:], eps) if dmax > eps else [a, b]
out = {}
for sgg, cnt in seg.items():
    edges = [e for e, n in cnt.items() if n == 1]
    adj = collections.defaultdict(list)
    for a, b in edges: adj[a].append(b); adj[b].append(a)
    used = set(); rings = []
    for a, b in edges:
        if (a, b) in used: continue
        ring = [a, b]; used.add((a, b)); used.add((b, a)); cur, prev = b, a
        while True:
            nxt = [n for n in adj[cur] if (cur, n) not in used]
            if not nxt: break
            n = nxt[0]; used.add((cur, n)); used.add((n, cur)); ring.append(n); prev, cur = cur, n
            if n == ring[0]: break
        if len(ring) > 3: rings.append(ring)
    paths, best, cen = [], 0, None
    for ring in rings:
        q = [proj(x) for x in ring]; h = len(q) // 2
        pp = dp(q[:h + 1], 0.35)[:-1] + dp(q[h:], 0.35)  # 닫힌 고리는 둘로 나눠 단순화 (시작=끝이면 기준선이 0 길이)
        if len(pp) < 4: continue
        paths.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pp) + 'Z')
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pp, pp[1:])) / 2
        if abs(area) > best:
            best = abs(area); cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(pp, pp[1:])) / (6 * area)
            cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(pp, pp[1:])) / (6 * area); cen = (round(cx, 1), round(cy, 1))
    out[sgg] = {'d': ''.join(paths), 'c': cen, 'a': round(best)}
out.pop('28720', None)  # 옹진군: 서해 섬까지 넣으면 지도가 너무 넓어진다
json.dump(out, open(ROOT / 'data/geo/sudogwon_sgg_20260701.json', 'w'), ensure_ascii=False, separators=(',', ':'))
xs = [float(v) for o in out.values() for v in __import__('re').findall(r'[-\d.]+', o['d'])]
print(len(out), 'regions', len(json.dumps(out)) // 1024, 'KB', 'x', min(xs[0::2]), max(xs[0::2]), 'y', min(xs[1::2]), max(xs[1::2]))
