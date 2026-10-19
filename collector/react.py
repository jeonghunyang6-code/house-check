"""F1 과거 입주 반응 (2026-10-19 sql/f1_react.sql 을 옮김: 전월세 단지 요약 과거분이 DB 가 아니라 rentsum 파일에 있어서).
📖 입주 물량이 전세를 누른다 p.154, p.423, 입주장 5~6개월 p.55, 반응표 p.63.

큰 입주(🔧 총 세대 500+, 2021-01 ~ 7개월 전)마다 같은 생활권 기존 단지(준공이 입주 2년 전 이전)의 전세 중앙가를
입주 전 6개월(T-6~T-1) 평균 대비 입주 후 6개월(T~T+5) 평균으로 비교하고, 같은 시도 전체(그 생활권 제외)의 같은 비교를 뺀다(%p).
단지·면적군마다 앞뒤 창에 계약이 다 있어야 하고(각 🔧 2건+), 생활권 쪽 🔧 5개 이상일 때만. 평균은 월별 중앙값의 건수 가중.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from statistics import median

MIN_HH, MIN_N, MIN_ZONE = 500, 2, 5
SINCE = "202007"


def r2(x: float) -> float:
    """PostgreSQL round(numeric, 2) 와 같게(0.5 는 0 에서 먼 쪽)."""
    return float(Decimal(repr(x)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def add_months(ym: str, k: int) -> str:
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 + k, 12)
    return f"{y}{m + 1:02d}"


def react_rows(events: list[dict], rents: list[tuple], cx: dict[str, tuple]) -> list[dict]:
    """events: house_no, z(생활권), move_in_ym, hh, sd('11'·'41'·'28')
    rents: (apt_seq, area_group, 계약월, 전세 중앙값, 전세 건수, sd) — 중앙값·건수 > 0 인 행
    cx: apt_seq → (생활권, 준공연도). 단지 표에 없는 단지는 뺀다
    → [{house_no, lifezone_id, move_in_ym, total_hh, zone_chg, base_chg, rel, n}]"""
    idx: dict[tuple[str, str], list[tuple]] = {}
    for r in rents:
        idx.setdefault((r[5], r[2]), []).append(r)
    out = []
    for e in events:
        y0 = int(e["move_in_ym"][:4])
        acc: dict[tuple[str, int], list] = {}
        for k in range(-6, 6):
            for a, ag, _, v, n, _ in idx.get((e["sd"], add_months(e["move_in_ym"], k)), ()):
                if a not in cx:
                    continue
                z, by = cx[a]
                if by is not None and by >= y0 - 1:
                    continue
                s = acc.setdefault((a, ag), [0.0, 0, 0.0, 0, z])
                i = 0 if k < 0 else 2
                s[i] += v * n
                s[i + 1] += n
        inside, outside = [], []
        for pv, pn, qv, qn, z in acc.values():
            if z is None or pn < MIN_N or qn < MIN_N or pv <= 0:
                continue
            (inside if z == e["z"] else outside).append((qv / qn) / (pv / pn))
        if len(inside) < MIN_ZONE:
            continue
        zr, br = median(inside), (median(outside) if outside else None)
        out.append(dict(house_no=e["house_no"], lifezone_id=e["z"], move_in_ym=e["move_in_ym"], total_hh=e["hh"],
                        zone_chg=r2((zr - 1) * 100), base_chg=None if br is None else r2((br - 1) * 100),
                        rel=None if br is None else r2((zr - br) * 100), n=len(inside)))
    return out


def zone_summary(rows: list[dict]) -> dict:
    """생활권 → (rel 중앙값, 사건 수)."""
    g: dict = {}
    for r in rows:
        g.setdefault(r["lifezone_id"], []).append(r["rel"])
    def med(v):   # rel 은 이미 소수 둘째 자리라 Decimal 로 평균해 반올림 경계에서 PostgreSQL 과 같게
        xs = [Decimal(repr(x)) for x in v if x is not None]
        return float(median(xs).quantize(Decimal("0.01"), ROUND_HALF_UP)) if xs else None
    return {z: (med(v), len(v)) for z, v in g.items()}
