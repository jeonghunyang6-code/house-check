"""E6 갈아타기 격차 서버 계산 (jobs/gap.py, 0049). 시안 ⑧ 과 같은 정의.

📖 갈아타기는 최소 1.5배(1.2배는 거래비용으로 상쇄) p.436~438 / 📖 격차가 줄어들 때 갈아탄다, 상승 초반엔 비싼 집이 먼저 올라 벌어지고 후반에 좁혀진다 p.438~439
/ 📖 수익률이 아니라 절대 금액 격차 p.418~420.
- 분기 가격 = 전용 84~85㎡(면적군 84·85) 중개·비해제·1층 제외 거래의 분기 중앙가, 최근 끝난 20분기
- 단지 = 🔧 12분기 이상 값이 있고 마지막 2분기 중 하나에 값이 있는 곳
- 목표 후보 = 🔧 직선 10km 안, 마지막 분기 가격이 1.5배 이상 🔧 2.5배 이하, 함께 거래된 분기 🔧 12개 이상이고 마지막 분기에 둘 다 값이 있는 곳
- 격차 위치 = 함께 거래된 분기들의 (목표 − 지금) 중 지금 격차 이하 비율(%). 낮을수록 격차가 좁아진 때(🔧 20 이하 = 축소 구간)
"""

from __future__ import annotations

import math
from datetime import date
from statistics import median
from typing import Iterable

N_Q, MIN_Q = 20, 12
MAX_M = 10_000
RATIO_LO, RATIO_HI = 1.5, 2.5
TOP = 5


def quarters(today: date, n: int = N_Q) -> list[str]:
    """끝난 분기 n개, 오래된 것부터 ('2026Q3')."""
    y, q = today.year, (today.month - 1) // 3
    if q == 0:
        y, q = y - 1, 4
    out = []
    for _ in range(n):
        out.append(f"{y}Q{q}")
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    return out[::-1]


def qkey(contract_month: str) -> str:
    return f"{contract_month[:4]}Q{(int(contract_month[4:6]) - 1) // 3 + 1}"


def quarter_medians(rows: Iterable[dict], qs: list[str]) -> dict[str, dict[str, float]]:
    """보관 파일 행(값은 문자열) → {apt_seq: {분기: 중앙가}}."""
    want, acc = set(qs), {}
    for r in rows:
        if r["is_cancelled"] in ("1", "True", "true", "t") or r["deal_type"] != "중개" or r.get("floor") == "1" or not r["area_m2"]:
            continue
        if math.floor(float(r["area_m2"])) not in (84, 85):
            continue
        q = qkey(r["contract_month"])
        if q in want:
            acc.setdefault(r["apt_seq"], {}).setdefault(q, []).append(int(r["price_10k"]))
    return {a: {q: median(v) for q, v in d.items()} for a, d in acc.items()}


def eligible(s: dict[str, float], qs: list[str]) -> bool:
    return sum(1 for q in qs if q in s) >= MIN_Q and (qs[-1] in s or qs[-2] in s)


def gap_stats(a: dict[str, float], b: dict[str, float], qs: list[str]) -> dict | None:
    g = [(q, b[q] - a[q]) for q in qs if q in a and q in b]
    if len(g) < MIN_Q or g[-1][0] != qs[-1]:
        return None
    cur = g[-1][1]
    return {"n_q": len(g), "gap_now_10k": round(cur), "gap_pct": round(sum(1 for _, v in g if v <= cur) * 100 / len(g), 1),
            "ratio_now": round(b[qs[-1]] / a[qs[-1]], 3)}


def dist_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return 111320 * math.hypot(lat2 - lat1, (lng2 - lng1) * 0.7934)


def targets(series: dict[str, dict[str, float]], coords: dict[str, tuple[float, float]], qs: list[str]) -> list[dict]:
    """[{apt_seq, rank, target_seq, ratio_now, gap_now_10k, gap_pct, n_q, dist_m}] 단지마다 격차 위치가 낮은 순 TOP 곳."""
    ok = [a for a, s in series.items() if eligible(s, qs) and a in coords and qs[-1] in s]
    out = []
    for a in ok:
        la, lo = coords[a]
        pa = series[a][qs[-1]]
        cands = []
        for b in ok:
            if b == a:
                continue
            ratio = series[b][qs[-1]] / pa
            if not (RATIO_LO <= ratio <= RATIO_HI):
                continue
            lb, lob = coords[b]
            if abs(lb - la) > 0.1 or abs(lob - lo) > 0.13:
                continue
            d = dist_m(la, lo, lb, lob)
            if d > MAX_M:
                continue
            st = gap_stats(series[a], series[b], qs)
            if st:
                cands.append(dict(st, target_seq=b, dist_m=round(d)))
        cands.sort(key=lambda c: (c["gap_pct"], c["ratio_now"]))
        out += [dict(c, apt_seq=a, rank=i + 1) for i, c in enumerate(cands[:TOP])]
    return out
