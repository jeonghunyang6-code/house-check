"""생활권 묶음 E0 (순수 함수). 📖 지역 묶음 = 생활권, 같은 묶음이면 시세 차이를 유지하며 함께 오르내린다 (p.468~470).

2026-10-15 방식 (행정동끼리 2년 가격만 보던 첫 실험은 서울 지역생활권을 못 가렸다):
1. 단위: 가장 가까운 역이 STATION_M 안인 단지는 그 역(S:역명), 아니면 행정동(D:adm_cd)  — 명세 "같은 최근접 역(1km)"
2. 후보 쌍: 같은 노선 이웃 역(LINE_NEIGHBOR_M 안 가까운 2개), 붙어 있는 행정동, 같은 행정동에 걸친 단위. 한강 건너는 빼고
3. 함께 움직였나: 단지마다 자기 중앙가로 나눈 ㎡당 가격의 분기 중앙값(구성 변화 보정) → 두 단위 지수 비율의 변동계수(CV)
4. CV 작은 쌍부터 묶되 🔧 CV_MAX, 묶음당 단위 MAX_UNITS·단지 MAX_COMPLEXES, 묶음 안 단위 중심끼리 MAX_SPAN_M 이내
🔧 값은 서울 지역생활권(116개)과의 단지 쌍 일치도(F1)로 정했다 (2026-10-15: 구 0.41, 단위만 0.47 → 0.59).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median, pstdev

from collector.infra import dist_m

STATION_M = 1000        # 📖 명세 E0: 같은 최근접 지하철역(1km 이내)
LINE_NEIGHBOR_M = 3000  # 같은 노선 이웃 역으로 볼 거리
MIN_QUARTERS = 12       # 비율 CV 에 필요한 공통 분기 (2020Q1~ 약 27분기)
CV_MAX = 0.10           # 🔧
MAX_UNITS = 6           # 🔧
MAX_COMPLEXES = 400     # 🔧
MAX_SPAN_M = 2000       # 🔧 묶음 안 단위 중심끼리 최대 거리 (없으면 노선을 따라 길게 이어진다: 목동~대방)


def unit_of(station_name: str | None, station_m: int | None, adm_cd: str | None) -> str | None:
    if station_name and station_m is not None and station_m <= STATION_M:
        return "S:" + station_name
    return "D:" + adm_cd if adm_cd else None


def unit_index(prices: dict[str, dict[str, float]], unit: dict[str, str], min_quarters: int = 4) -> dict[str, dict[str, float]]:
    """prices: 단지 → 분기 → ㎡당 중앙가. 단지마다 자기 중앙가로 나눠(구성 보정) 단위·분기별 중앙값. 단지 2개 이상인 분기만."""
    rel: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for k, qs in prices.items():
        if k not in unit or len(qs) < min_quarters:
            continue
        base = median(qs.values())
        for q, p in qs.items():
            rel[unit[k]][q].append(p / base)
    return {u: {q: median(v) for q, v in qs.items() if len(v) >= 2} for u, qs in rel.items()}


def ratio_cv(a: dict[str, float], b: dict[str, float], min_quarters: int = MIN_QUARTERS) -> float | None:
    qs = sorted(set(a) & set(b))
    if len(qs) < min_quarters:
        return None
    r = [a[q] / b[q] for q in qs]
    m = mean(r)
    return pstdev(r) / m if m else None


def candidate_pairs(units: dict[str, dict], stations: dict[str, dict], adm_adj: list[tuple[str, str]]) -> set[tuple[str, str]]:
    """units: u → {adms: Counter(adm_cd), side: 한강 남북}. stations: 역명 → {lat, lng, lines(set)}."""
    pairs: set[tuple[str, str]] = set()
    for u in units:
        if not u.startswith("S:") or u[2:] not in stations:
            continue
        s = stations[u[2:]]
        for ln in s["lines"]:
            near = sorted((dist_m(s["lat"], s["lng"], o["lat"], o["lng"]), n) for n, o in stations.items()
                          if n != u[2:] and ln in o["lines"])
            for d, n in near[:2]:
                if d <= LINE_NEIGHBOR_M and "S:" + n in units:
                    pairs.add(tuple(sorted((u, "S:" + n))))
    by_adm: dict[str, set[str]] = defaultdict(set)
    for u, info in units.items():
        for a in info["adms"]:
            by_adm[a].add(u)
    for a, b in adm_adj:
        for x in by_adm.get(a, ()):
            for y in by_adm.get(b, ()):
                if x != y:
                    pairs.add(tuple(sorted((x, y))))
    for us in by_adm.values():
        for x in us:
            for y in us:
                if x < y:
                    pairs.add((x, y))
    return {p for p in pairs if not (units[p[0]].get("side") and units[p[1]].get("side") and units[p[0]]["side"] != units[p[1]]["side"])}


def merge(units: dict[str, dict], scored: list[tuple[float, str, str]], cv_max: float = CV_MAX, max_units: int = MAX_UNITS,
          max_complexes: int = MAX_COMPLEXES, max_span_m: float = MAX_SPAN_M) -> dict[str, str]:
    """units: u → {n: 단지 수, lat, lng(중심)}. scored: (CV, a, b). → u → 묶음 대표 u."""
    root = {u: u for u in units}
    mem = {u: [u] for u in units}
    n = {u: units[u]["n"] for u in units}

    def find(x):
        while root[x] != x:
            root[x] = root[root[x]]
            x = root[x]
        return x

    for cv, a, b in sorted(scored):
        if cv > cv_max:
            break
        ra, rb = find(a), find(b)
        if ra == rb or len(mem[ra]) + len(mem[rb]) > max_units or n[ra] + n[rb] > max_complexes:
            continue
        if any(dist_m(units[x]["lat"], units[x]["lng"], units[y]["lat"], units[y]["lng"]) > max_span_m for x in mem[ra] for y in mem[rb]):
            continue
        root[rb] = ra
        mem[ra] += mem.pop(rb)
        n[ra] += n[rb]
    return {u: find(u) for u in units}


def pair_f1(group: dict[str, str], ref: dict[str, str], block: dict[str, str]) -> tuple[float, float, float]:
    """단지 쌍 일치도. group·ref: 단지 → 묶음, block: 단지 → 비교 범위(같은 구 안 쌍만 센다: 서울 지역생활권은 구를 넘지 않는다)."""
    by: dict[str, list[str]] = defaultdict(list)
    for k in group:
        if k in ref and k in block:
            by[block[k]].append(k)
    tp = fp = fn = 0
    for ks in by.values():
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                g, r = group[a] == group[b], ref[a] == ref[b]
                tp += g and r
                fp += g and not r
                fn += r and not g
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def zone_name(units: list[str], n: dict[str, int], adm_nm: dict[str, str]) -> str:
    """단지가 많은 단위부터 이름 3개: 역은 '잠실', 행정동은 '잠실2동'."""
    names = []
    for u in sorted(units, key=lambda x: -n.get(x, 0)):
        nm = u[2:] if u.startswith("S:") else adm_nm.get(u[2:], u[2:]).split()[-1]
        if nm not in names:
            names.append(nm)
    return "·".join(names[:3])


def majority(c: Counter):
    return c.most_common(1)[0][0] if c else None
