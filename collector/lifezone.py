"""생활권 묶음 E0 (순수 함수). 📖 지역 묶음 = 생활권, 같은 묶음이면 시세 차이를 유지하며 함께 오르내린다 (p.468~470).

단위는 행정동(adm_dong, 인접 adm_adjacent). 붙어 있는 두 동의 분기별 84㎡ 환산 중앙가 비율이 얼마나 일정했는지(변동계수 CV)로
'함께 움직였나'를 재고, 작은 CV 쌍부터 묶는다(union-find). 🔧 CV 상한·묶음 크기 상한은 서울 지역생활권(116개, 3~5개 동)과의
일치도로 정한다. 한강 건너 쌍은 묶지 않는다(2026-10-14 사용자 결정). 거래가 적어 지수가 없는 동은 강을 건너지 않는 이웃 중
가격 수준이 가장 가까운 묶음에 붙인다.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev

MIN_DEALS = 3        # 분기 지수에 필요한 최소 거래
MIN_QUARTERS = 5     # 비율 CV 에 필요한 공통 분기
CV_MAX = 0.06        # 🔧 이 이하면 '함께 움직임'
MAX_SIZE = 6         # 🔧 묶음당 최대 행정동 수


def quarter_index(rows: list[tuple[str, str, float]]) -> dict[str, dict[str, float]]:
    """(adm_cd, 분기 'YYYYQn', 84㎡ 환산가) → adm_cd → 분기 → 중앙값 (거래 MIN_DEALS 이상인 분기만)."""
    g: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for cd, q, p in rows:
        g[cd][q].append(p)
    return {cd: {q: median(v) for q, v in qs.items() if len(v) >= MIN_DEALS} for cd, qs in g.items()}


def ratio_cv(a: dict[str, float], b: dict[str, float]) -> float | None:
    qs = sorted(set(a) & set(b))
    if len(qs) < MIN_QUARTERS:
        return None
    r = [a[q] / b[q] for q in qs]
    m = mean(r)
    return pstdev(r) / m if m else None


def level(ix: dict[str, float]) -> float | None:
    return median(ix.values()) if ix else None


class _UF:
    def __init__(self, items):
        self.p = {i: i for i in items}
        self.size = {i: 1 for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if self.size[ra] < self.size[rb]:
                ra, rb = rb, ra
            self.p[rb] = ra
            self.size[ra] += self.size[rb]


def cluster(dongs: list[str], adj: list[tuple[str, str, bool]], index: dict[str, dict[str, float]],
            cv_max: float = CV_MAX, max_size: int = MAX_SIZE) -> dict[str, str]:
    """→ adm_cd → 묶음 대표 adm_cd. adj: (a, b, 한강 건너)."""
    uf = _UF(dongs)
    edges = []
    for a, b, river in adj:
        if river or a not in uf.p or b not in uf.p:
            continue
        cv = ratio_cv(index.get(a, {}), index.get(b, {}))
        if cv is not None and cv <= cv_max:
            edges.append((cv, a, b))
    for cv, a, b in sorted(edges):
        ra, rb = uf.find(a), uf.find(b)
        if ra != rb and uf.size[ra] + uf.size[rb] <= max_size:
            uf.union(ra, rb)
    # 지수 없는 동: 강을 건너지 않는 이웃 묶음 중 가격 수준이 가장 가까운 곳 (수준을 모르면 경계를 가장 많이 맞댄 이웃은 모르므로 첫 이웃)
    nbr = defaultdict(list)
    for a, b, river in adj:
        if not river:
            nbr[a].append(b)
            nbr[b].append(a)
    lv = {d: level(index.get(d, {})) for d in dongs}
    for d in dongs:
        if lv[d] is None and uf.size[uf.find(d)] == 1 and nbr[d]:
            cands = [n for n in nbr[d] if n in uf.p and lv.get(n) is not None] or [n for n in nbr[d] if n in uf.p]
            if cands:
                uf.union(cands[0], d)
    return {d: uf.find(d) for d in dongs}


def agreement(groups: dict[str, str], ref: dict[str, str], adj: list[tuple[str, str, bool]]) -> dict[str, float]:
    """인접 쌍 기준 일치도. both: 둘 다 같은 묶음, ref_same 중 같이 묶인 비율(재현율), 같이 묶인 것 중 ref 도 같은 비율(정밀도)."""
    tp = fp = fn = tn = 0
    for a, b, _ in adj:
        if a in groups and b in groups and a in ref and b in ref:
            g, r = groups[a] == groups[b], ref[a] == ref[b]
            tp += g and r
            fp += g and not r
            fn += (not g) and r
            tn += (not g) and (not r)
    n = tp + fp + fn + tn
    return {"pairs": n, "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
            "accuracy": (tp + tn) / n if n else 0.0}
