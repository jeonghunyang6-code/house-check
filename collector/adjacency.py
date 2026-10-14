"""행정동 경계 → 면적·중심·인접 (순수 함수, jobs/geo.py boundary). 좌표는 SGIS 경계의 UTM-K(EPSG:5179, 미터).

인접: SGIS 경계는 동마다 따로 단순화돼 맞닿은 변이라도 꼭짓점이 서로 맞지 않는다(2026-10-14 실측: 꼭짓점 칸 비교로는
강동구 성내3동 이웃 0, 잠실2동 이웃에서 잠실본동·6동 빠짐). 그래서 A 의 꼭짓점이 B 의 경계선(선분)에서 TOL_M 안에 있는
개수를 세고, 양방향 중 큰 값이 MIN_SHARED 이상이면 인접으로 본다(점 하나로만 닿은 모서리는 제외). 선분은 CELL_M 격자로 찾는다.
한강: 경계가 강 가운데서 맞닿아 성수동(성동구)·압구정동(강남구)처럼 강 건너도 인접으로 나온다.
     시군구별 강 남북(HAN_SIDE)이 서로 다르면 cross_river 로 표시만 하고, 묶을지는 생활권(E0) 단계에서 정한다.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

TOL_M = 30.0
CELL_M = 100.0
MIN_SHARED = 2

# 한강 남북 (시군구 이름). 서울은 어느 구도 강을 걸치지 않는다. 경기는 강에 닿는 곳만, 양평처럼 걸치는 곳은 넣지 않는다
HAN_SIDE = {
    **{g: "N" for g in ("종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구",
                        "노원구", "은평구", "서대문구", "마포구", "고양시", "파주시", "남양주시", "구리시")},
    **{g: "S" for g in ("강서구", "양천구", "구로구", "영등포구", "금천구", "동작구", "관악구", "서초구", "강남구", "송파구",
                        "강동구", "김포시", "하남시")},
}


def rings(geom: dict) -> list[list[list[float]]]:
    """Polygon / MultiPolygon → 바깥 고리 목록 (구멍 제외)."""
    t, c = geom.get("type"), geom.get("coordinates") or []
    if t == "Polygon":
        return [c[0]] if c else []
    if t == "MultiPolygon":
        return [p[0] for p in c if p]
    return []


def area_centroid(geom: dict) -> tuple[float, float, float]:
    """(면적 m², 중심 x, 중심 y). 신발끈 공식, 여러 조각이면 면적 가중."""
    A = cx = cy = 0.0
    for r in rings(geom):
        a = sx = sy = 0.0
        for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
            cr = x0 * y1 - x1 * y0
            a += cr
            sx += (x0 + x1) * cr
            sy += (y0 + y1) * cr
        if a:
            A += a / 2
            cx += sx / 6
            cy += sy / 6
    if not A:
        return 0.0, 0.0, 0.0
    return abs(A), cx / A, cy / A


def side_of(adm_nm: str) -> str | None:
    """'서울특별시 송파구 풍납1동' → 'S', '경기도 고양시 덕양구 …' → 'N'."""
    for tok in adm_nm.split()[1:3]:
        if tok in HAN_SIDE:
            return HAN_SIDE[tok]
    return None


def _seg_dist2(px: float, py: float, x0: float, y0: float, x1: float, y1: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L))
    qx, qy = x0 + t * dx - px, y0 + t * dy - py
    return qx * qx + qy * qy


def adjacency(features: list[dict]) -> list[tuple[str, str, int, bool]]:
    """features: {'adm_cd', 'adm_nm', 'geometry'} → [(a, b, 가까운 꼭짓점 수, 한강 건너)] (a < b)."""
    names = {f["adm_cd"]: f.get("adm_nm", "") for f in features}
    segs: dict[tuple[int, int], list[tuple[str, float, float, float, float]]] = defaultdict(list)
    verts: list[tuple[str, float, float]] = []
    for f in features:
        cd = f["adm_cd"]
        for r in rings(f["geometry"]):
            for (x0, y0), (x1, y1) in zip(r, r[1:]):
                for i in range(int(min(x0, x1) // CELL_M), int(max(x0, x1) // CELL_M) + 1):
                    for j in range(int(min(y0, y1) // CELL_M), int(max(y0, y1) // CELL_M) + 1):
                        segs[(i, j)].append((cd, x0, y0, x1, y1))
            verts += [(cd, x, y) for x, y in r[:-1]]
    tol2 = TOL_M * TOL_M
    near: dict[tuple[str, str], int] = defaultdict(int)   # (A, B) → B 의 경계선 가까이 있는 A 의 꼭짓점 수
    for cd, x, y in verts:
        ci, cj = int(x // CELL_M), int(y // CELL_M)
        hit = set()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for other, x0, y0, x1, y1 in segs.get((ci + di, cj + dj), ()):
                    if other != cd and other not in hit and _seg_dist2(x, y, x0, y0, x1, y1) <= tol2:
                        hit.add(other)
        for other in hit:
            near[(cd, other)] += 1
    out = []
    for a, b in sorted({tuple(sorted(k)) for k in near}):
        n = max(near.get((a, b), 0), near.get((b, a), 0))
        if n >= MIN_SHARED:
            sa, sb = side_of(names[a]), side_of(names[b])
            out.append((a, b, n, bool(sa and sb and sa != sb)))
    return out
