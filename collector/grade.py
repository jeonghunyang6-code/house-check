"""급지 E1: 법정동 대표가와 8단계 급지, 보조 표시 3개 (docs/HANDOFF.md 급지 E1 확정, 2026-10-13).

대표가 = 단지별 84㎡ 환산 중앙값(최근 1년, 중개·비해제, 전용 40~135㎡, 2건+)을 거래 건수로 가중한 중앙값.
300세대 미만 단지 거래는 SMALL_W 로 가중한다. 연식 보정은 하지 않는다(사용자 결정: 실거래가 그대로).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# 경계(억, 84㎡ 환산 실거래 대표가). 15억·25억 = 주담대 상한 경계(10·15 대책: ≤15억 6억, ≤25억 4억, 초과 2억), 나머지 🔧
CUTS = (30, 25, 20, 15, 12, 9, 6)
SMALL_W = 0.3          # 🔧 300세대 미만 단지 거래 가중치
SMALL_HH = 300
UNKNOWN_BIG_N = 20     # 🔧 K-apt 미연결 단지는 1년 거래 20건 이상이면 대단지로 본다
MIN_COMPLEXES = 3
OLD_YEARS = 30         # 재건축 기대: 30년+ 단지 거래 비중 ≥ 50% (📖 재건축 p.374~397)
OLD_SHARE = 0.5
GAP_RATIO = 2.0        # 🔧 동 안 격차: 가중 상위 25% ÷ 하위 25% ≥ 2배
NEW_YEARS = 5          # 🔧 신축 대단지: 준공 5년 이내(급지 분석의 신축 구간), 1,000세대 이상
NEW_HH = 1000


@dataclass
class Complex:
    region_code: str
    umd_name: str
    name: str
    build_year: int
    p84_10k: float     # 84㎡ 환산 중앙값 (만원)
    n: int             # 최근 1년 거래 건수
    households: int | None


def grade_of(value_eok: float) -> int:
    """1(최상) ~ 8."""
    return 1 + sum(1 for c in CUTS if value_eok < c)


def is_small(c: Complex) -> bool:
    if c.households is None or c.households <= 0:
        return c.n < UNKNOWN_BIG_N
    return c.households < SMALL_HH


def wquantile(xs: list[tuple[float, float]], q: float) -> float:
    xs = sorted(xs)
    tot = sum(w for _, w in xs)
    acc = 0.0
    for v, w in xs:
        acc += w
        if acc >= tot * q:
            return v
    return xs[-1][0]


def dong_grades(complexes: list[Complex], year: int) -> list[dict]:
    by: dict[tuple[str, str], list[Complex]] = defaultdict(list)
    for c in complexes:
        by[(c.region_code, c.umd_name)].append(c)
    out = []
    for (rc, umd), cs in by.items():
        if len(cs) < MIN_COMPLEXES:
            continue
        xs = [(c.p84_10k, c.n * (SMALL_W if is_small(c) else 1.0)) for c in cs]
        value = wquantile(xs, 0.5)
        q1, q3 = wquantile(xs, 0.25), wquantile(xs, 0.75)
        n = sum(c.n for c in cs)
        old = sum(c.n for c in cs if year - c.build_year >= OLD_YEARS) / n
        new = [c for c in cs if year - c.build_year <= NEW_YEARS and (c.households or 0) >= NEW_HH]
        nb = max(new, key=lambda c: c.households or 0) if new else None
        out.append(dict(region_code=rc, umd_name=umd, grade=grade_of(value / 1e4), value_10k=round(value),
                        q1_10k=round(q1), q3_10k=round(q3), n_complex=len(cs), n_deals=n, old_share=round(old, 3),
                        flag_rebuild=old >= OLD_SHARE, flag_gap=q1 > 0 and q3 / q1 >= GAP_RATIO,
                        new_big_name=nb.name if nb else None, new_big_10k=round(nb.p84_10k) if nb else None))
    return out
