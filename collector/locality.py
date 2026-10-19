"""E8 상급지까지 거리 (관점 D1, 📖 입지 = 업무지구·학군·상급지와의 절대거리 p.85~103). jobs/locality.py → complex_e8 (0052).

업무지구는 H2(대중교통 시간), 학군은 H3(학원·학교), 여기서는 상급지만: 급지 E1(dong_grade 최신) 기준
- 위 급지 = 이 단지 동보다 급지 숫자가 작은(비싼) 동 중 가장 가까운 동
- 최상급지 = 🔧 1~2급지(84㎡ 환산 25억+) 동 중 가장 가까운 동
거리 = 단지 좌표 → 그 동 단지들 좌표 평균(동 중심) 직선거리. 급지 없는 동(거래 적음)의 단지는 위 급지를 비운다.
"""

from __future__ import annotations

from collector.gap import dist_m

TOP_GRADE = 2


def centroids(rows: list[dict]) -> dict[tuple[str, str], tuple[float, float]]:
    """rows: region_code, umd_name, lat, lng → 동별 좌표 평균."""
    acc: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for r in rows:
        if r["lat"] is not None and r["lng"] is not None and r["umd_name"]:
            acc.setdefault((r["region_code"], r["umd_name"]), []).append((float(r["lat"]), float(r["lng"])))
    return {k: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for k, v in acc.items()}


def nearest(lat: float, lng: float, cands: list[tuple[tuple[str, str], int, tuple[float, float]]]):
    best = None
    for key, g, (la, lo) in cands:
        d = dist_m(lat, lng, la, lo)
        if best is None or d < best[2]:
            best = (key, g, d)
    return best


def e8_rows(complexes: list[dict], grades: dict[tuple[str, str], int], cents: dict[tuple[str, str], tuple[float, float]]) -> list[dict]:
    """complexes: apt_seq, region_code, umd_name, lat, lng → [{apt_seq, grade, up_*, top_*}] 좌표 있는 단지만."""
    pts = sorted(((k, g, cents[k]) for k, g in grades.items() if k in cents), key=lambda x: x[1])
    by_lt: dict[int, list] = {g: [p for p in pts if p[1] < g] for g in range(1, 9)}
    top = [p for p in pts if p[1] <= TOP_GRADE]
    out = []
    for c in complexes:
        if c["lat"] is None or c["lng"] is None:
            continue
        la, lo = float(c["lat"]), float(c["lng"])
        g = grades.get((c["region_code"], c["umd_name"]))
        up = nearest(la, lo, by_lt[g]) if g else None
        tp = nearest(la, lo, top) if not (g and g <= TOP_GRADE) else None
        out.append(dict(apt_seq=c["apt_seq"], grade=g,
                        up_rc=up[0][0] if up else None, up_dong=up[0][1] if up else None, up_grade=up[1] if up else None,
                        up_m=round(up[2]) if up else None,
                        top_rc=tp[0][0] if tp else None, top_dong=tp[0][1] if tp else None, top_m=round(tp[2]) if tp else None))
    return out
