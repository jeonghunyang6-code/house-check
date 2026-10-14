"""행정동 경계 → 면적·중심·인접 (순수 함수, jobs/geo.py boundary). 좌표는 SGIS 경계의 UTM-K(EPSG:5179, 미터).

인접: 맞닿은 변은 두 경계의 꼭짓점이 가까이 모인다. 꼭짓점을 CELL_M 격자에 넣고, A 의 꼭짓점이 있는 칸 둘레(3×3)에
B 의 꼭짓점이 있는 칸이 MIN_SHARED 개 이상이면 인접으로 센다(점 하나로만 닿은 모서리는 제외).
2026-10-14 첫 실행(같은 칸만 셈): 꼭짓점이 몇 m 어긋난 곳을 놓침(강동구 성내3동 이웃 0, 잠실2동 이웃 일부 빠짐) → 3×3 이웃 칸까지.
한강: 경계가 강 가운데서 맞닿아 성수동(성동구)·압구정동(강남구)처럼 강 건너도 인접으로 나온다.
     시군구별 강 남북(HAN_SIDE)이 서로 다르면 cross_river 로 표시만 하고, 묶을지는 생활권(E0) 단계에서 정한다.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

CELL_M = 15.0
MIN_SHARED = 4

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
    hits: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)   # 쌍 → A 쪽 칸 (B 가 3×3 안에 있는)
    for (i, j), owners in cells.items():
        near = set()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                near |= cells.get((i + di, j + dj), set())
        for a in owners:
            for b in near:
                if a < b:
                    hits[(a, b)].add((i, j))
                elif b < a:
                    hits[(b, a)].add((i, j))
    shared = {k: len(v) for k, v in hits.items()}
    out = []
    for (a, b), n in sorted(shared.items()):
        if n >= MIN_SHARED:
            sa, sb = side_of(names[a]), side_of(names[b])
            out.append((a, b, n, bool(sa and sb and sa != sb)))
    return out
