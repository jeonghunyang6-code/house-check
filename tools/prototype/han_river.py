"""한강 선(시장 탭 지도): SGIS 행정동 경계(Releases raw-data hadm_2025.geojson.gz, jobs/geo.py boundary 가 올림, EPSG:5179)에서
한강 북쪽 시군구 동과 남쪽 시군구 동이 맞닿는 변 = 한강 가운데 선. geo.py 와 같은 화면 좌표로 바꿔 data/geo/han_river_2025.json.

    python tools/prototype/han_river.py hadm_2025.geojson.gz
"""
import collections, gzip, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
d = json.loads(gzip.decompress(open(sys.argv[1], 'rb').read()))
N = ['서울특별시 마포구', '서울특별시 용산구', '서울특별시 성동구', '서울특별시 광진구', '경기도 고양시 덕양구', '경기도 고양시 일산서구', '경기도 고양시 일산동구', '경기도 구리시', '경기도 남양주시', '경기도 파주시']
S = ['서울특별시 강서구', '서울특별시 영등포구', '서울특별시 동작구', '서울특별시 서초구', '서울특별시 강남구', '서울특별시 송파구', '서울특별시 강동구', '경기도 김포시', '경기도 하남시']
side = lambda nm: 'N' if any(nm.startswith(x + ' ') for x in N) else 'S' if any(nm.startswith(x + ' ') for x in S) else None
seg = collections.defaultdict(set)
R = lambda p: (round(p[0], 1), round(p[1], 1))
for f in d['features']:
    s = side(f['properties']['adm_nm'])
    if not s: continue
    g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in polys:
        for ring in poly:
            pts = [R(q) for q in ring]
            for a, b in zip(pts, pts[1:]):
                if a != b: seg[tuple(sorted((a, b)))].add(s)
river = [e for e, ss in seg.items() if ss == {'N', 'S'}]
# EPSG:5179 (UTM-K, GRS80) → 경위도. 횡메르카토르 역변환(Snyder)
a, f = 6378137.0, 1 / 298.257222101
e2 = f * (2 - f); ep2 = e2 / (1 - e2); k0 = 0.9996; lat0, lon0 = math.radians(38), math.radians(127.5); FE, FN = 1000000.0, 2000000.0
def M(phi): return a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
                        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi) - (35 * e2**3 / 3072) * math.sin(6 * phi))
M0 = M(lat0)
def inv(x, y):
    m = M0 + (y - FN) / k0; mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256)); e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu) + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu) + (151 * e1**3 / 96) * math.sin(6 * mu) + (1097 * e1**4 / 512) * math.sin(8 * mu)
    C1 = ep2 * math.cos(p1)**2; T1 = math.tan(p1)**2; N1 = a / math.sqrt(1 - e2 * math.sin(p1)**2); R1 = a * (1 - e2) / (1 - e2 * math.sin(p1)**2)**1.5; D = (x - FE) / (N1 * k0)
    lat = p1 - (N1 * math.tan(p1) / R1) * (D**2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * ep2) * D**4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * ep2 - 3 * C1**2) * D**6 / 720)
    lon = lon0 + (D - (1 + 2 * T1 + C1) * D**3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * ep2 + 24 * T1**2) * D**5 / 120) / math.cos(p1)
    return math.degrees(lon), math.degrees(lat)
K = math.cos(math.radians(37.5))
def proj(pt): return ((pt[0] - 126.0) * K * 1000, (38.4 - pt[1]) * 1000)
def dp(pts, eps):
    if len(pts) < 3: return pts
    A, B = pts[0], pts[-1]; dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1e-9
    i, dmax = 0, 0
    for k in range(1, len(pts) - 1):
        d = abs(dy * (pts[k][0] - A[0]) - dx * (pts[k][1] - A[1])) / L
        if d > dmax: i, dmax = k, d
    return dp(pts[:i + 1], eps)[:-1] + dp(pts[i:], eps) if dmax > eps else [A, B]
segs = river
adj = collections.defaultdict(list)
for a_, b_ in segs: adj[a_].append(b_); adj[b_].append(a_)
used = set(); chains = []
ends = [p for p, n in adj.items() if len(n) == 1] + list(adj)
for st in ends:
    for nb in adj[st]:
        if (st, nb) in used: continue
        ch = [st, nb]; used |= {(st, nb), (nb, st)}; cur = nb
        while len(adj[cur]) == 2:
            nx = [n for n in adj[cur] if (cur, n) not in used]
            if not nx: break
            used |= {(cur, nx[0]), (nx[0], cur)}; ch.append(nx[0]); cur = nx[0]
        chains.append(ch)
paths = []
for ch in chains:
    q = dp([proj(inv(*p)) for p in ch], 0.25)
    if len(q) >= 2: paths.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in q))
print(len(chains), 'chains', sum(len(c) for c in chains), 'pts', len(''.join(paths)), 'chars')
json.dump({'d': ''.join(paths), 'src': 'SGIS 행정동 경계(2025, Releases raw-data hadm_2025) 중 한강 북쪽·남쪽 시군구 동이 맞닿는 선 = 한강 가운데 선'}, open(ROOT / 'data/geo/han_river_2025.json', 'w'), ensure_ascii=False)
