"""행정동 경계 → 면적·중심·인접 (순수 함수, jobs/geo.py boundary). 좌표는 SGIS 경계의 UTM-K(EPSG:5179, 미터).

인접: 두 경계가 꼭짓점을 함께 쓰면(같은 지형 자료라 맞닿은 변의 꼭짓점이 겹친다) 붙어 있다고 본다.
꼭짓점을 CELL_M 격자로 묶고, 같은 칸을 MIN_SHARED 개 이상 함께 쓰는 쌍을 인접으로 센다(점 하나로만 닿은 모서리는 제외).
한강: 경계가 강 가운데서 맞닿아 성수동(성동구)·압구정동(강남구)처럼 강 건너도 인접으로 나온다.
     시군구별 강 남북(HAN_SIDE)이 서로 다르면 cross_river 로 표시만 하고, 묶을지는 생활권(E0) 단계에서 정한다.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

CELL_M = 20.0
MIN_SHARED = 3

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


def adjacency(features: list[dict]) -> list[tuple[str, str, int, bool]]:
    """features: {'adm_cd', 'adm_nm', 'geometry'} → [(a, b, 함께 쓰는 칸 수, 한강 건너)] (a < b)."""
    cells: dict[tuple[int, int], set[str]] = defaultdict(set)
    names = {}
    for f in features:
        cd = f["adm_cd"]
        names[cd] = f.get("adm_nm", "")
        for r in rings(f["geometry"]):
            for x, y in r:
                cells[(int(x // CELL_M), int(y // CELL_M))].add(cd)
    shared: dict[tuple[str, str], int] = defaultdict(int)
    for owners in cells.values():
        if len(owners) > 1:
            for a, b in combinations(sorted(owners), 2):
                shared[(a, b)] += 1
    out = []
    for (a, b), n in sorted(shared.items()):
        if n >= MIN_SHARED:
            sa, sb = side_of(names[a]), side_of(names[b])
            out.append((a, b, n, bool(sa and sb and sa != sb)))
    return out
