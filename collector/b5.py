"""B5 ② 하위 급지 신고가 비중의 월별 과거 시계열 (경고선 백테스트용). jobs/b5_history.py 가 쓴다.

신고가 = 같은 단지·같은 면적군(area_group = floor(전용))의 그 이전 계약일 중개·비해제 최고가보다 높은 거래 (sql/metrics.sql prev_high 와 같은 정의:
같은 날 거래는 '이전'이 아니다). 하위 급지 = 6~8급, 상위 = 1~3급 (지금 dong_grade 를 과거에도 쓴다 — 한계).
립밤(📖 p.111~114) = 하위 급지 중 준공 20년+·300세대 미만.
C11(2026-11-17, 송희구 부읽남TV 26-11-06 34:40 '경기 완전 외곽까지 들썩여야 후반'): 경기(41) 7급·8급 따로(g7·g8) → 끝물 🔧 기준선 백테스트.
"""

from __future__ import annotations

import math
from collections import defaultdict


def valid(r: dict) -> bool:
    return r["deal_type"] == "중개" and str(r["is_cancelled"]) not in ("1", "True", "true", "t")


def monthly(rows: list[dict], cx: dict[str, dict], from_month: str = "202101") -> dict[str, dict]:
    """rows: 거래(값은 문자열이어도 된다). cx: apt_seq → {grade, build_year, households}."""
    by: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if valid(r):
            by[(r["apt_seq"], math.floor(float(r["area_m2"])))].append(r)
    out: dict[str, dict] = defaultdict(lambda: dict(n_low=0, h_low=0, n_top=0, h_top=0, n_lip=0, h_lip=0, n_g7=0, h_g7=0, n_g8=0, h_g8=0))
    for (seq, _), rs in by.items():
        c = cx.get(seq)
        if not c or c.get("grade") is None:
            continue
        g = c["grade"]
        if 3 < g < 6:
            continue
        rs.sort(key=lambda r: str(r["contract_date"]))
        hi, i = None, 0
        while i < len(rs):
            d = str(rs[i]["contract_date"])
            j = i
            while j < len(rs) and str(rs[j]["contract_date"]) == d:
                j += 1
            day = rs[i:j]
            m = d[:4] + d[5:7]
            if hi is not None and m >= from_month:
                o = out[m]
                lip = g >= 6 and c.get("build_year") is not None and int(c["build_year"]) <= int(m[:4]) - 20 and (c.get("households") or 0) < 300
                gk = f"g{g}" if g in (7, 8) and str(c.get("region_code") or "").startswith("41") else None
                for r in day:
                    h = int(r["price_10k"]) > hi
                    if g >= 6:
                        o["n_low"] += 1; o["h_low"] += h
                    else:
                        o["n_top"] += 1; o["h_top"] += h
                    if lip:
                        o["n_lip"] += 1; o["h_lip"] += h
                    if gk:
                        o["n_" + gk] += 1; o["h_" + gk] += h
            mx = max(int(r["price_10k"]) for r in day)
            hi = mx if hi is None else max(hi, mx)
            i = j
    return dict(sorted(out.items()))
