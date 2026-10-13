"""보관 파일(deals_YYYYMM.csv.gz)에서 과거 고정값 계산 (저장 구조 C, 2026-10-14).

DB 에는 매매 원본을 최근 2년만 둔다. 그 이전 거래가 필요한 지표는 여기서 한 번 계산해 deal_anchor 표로 둔다.
sql/metrics.sql 의 정의와 같게 계산한다 (중개·비해제, area_group = floor(전용)):
- hist_high: 보관 구간의 최고가(같으면 이른 계약일) → 전고점(prev_high)·역대 최고(high_10k)에 DB 구간과 합친다
- peak / trough: 월별 기준 시세(그 달 포함 3개월 중앙값) 2021-01~2022-06 최고, 2022-07~2023-06 최저 (B2)
- p20: 2020년 1분기 중앙값 (A6)
deal_region_month: 시군구 × 계약월 거래 수, 전용 84~85㎡(area_group) 중개 중앙값 (시안 월별 차트용, extract.py 와 같은 정의)
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from statistics import median

ANCHOR_COLUMNS = ("apt_seq", "area_group", "hist_high_10k", "hist_high_date", "peak_10k", "peak_m", "trough_10k",
                  "trough_m", "p20_10k")
REGION_MONTH_COLUMNS = ("region_code", "contract_month", "n_all", "n_broker", "n_direct", "n_cancelled", "p84_median_10k")


def _months(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    out, (y, m) = [], a
    while (y, m) <= b:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


REF_MONTHS = _months((2021, 1), (2023, 6))
PEAK_END = (2022, 6)


def _back(ym: tuple[int, int], k: int) -> tuple[int, int]:
    y, m = ym
    m -= k
    while m < 1:
        y, m = y - 1, m + 12
    return y, m


def anchors(rows: list[dict]) -> list[dict]:
    """rows: 보관 파일 decode 결과(값은 문자열)."""
    by_month: dict[tuple, dict[tuple[int, int], list[int]]] = defaultdict(lambda: defaultdict(list))
    hi: dict[tuple, tuple[int, str]] = {}
    q120: dict[tuple, list[int]] = defaultdict(list)
    for r in rows:
        if r["is_cancelled"] in ("1", "True", "true", "t") or r["deal_type"] != "중개":
            continue
        k = (r["apt_seq"], math.floor(float(r["area_m2"])))
        p, d = int(r["price_10k"]), r["contract_date"]
        if k not in hi or p > hi[k][0] or (p == hi[k][0] and d < hi[k][1]):
            hi[k] = (p, d)
        y, m = int(d[:4]), int(d[5:7])
        by_month[k][(y, m)].append(p)
        if d < "2020-04-01" and d >= "2020-01-01":
            q120[k].append(p)
    out = []
    for k, (hp, hd) in hi.items():
        bm = by_month[k]
        ref = {}
        for ym in REF_MONTHS:
            xs = bm.get(ym, []) + bm.get(_back(ym, 1), []) + bm.get(_back(ym, 2), [])
            if xs:
                ref[ym] = median(xs)
        pk = [(v, ym) for ym, v in ref.items() if ym <= PEAK_END]
        tr = [(v, ym) for ym, v in ref.items() if ym > PEAK_END]
        p = max(pk, key=lambda t: (t[0], (-t[1][0], -t[1][1]))) if pk else None   # 같으면 이른 달
        t = min(tr, key=lambda t: (t[0], t[1])) if tr else None
        out.append(dict(apt_seq=k[0], area_group=k[1], hist_high_10k=hp, hist_high_date=hd,
                        peak_10k=round(p[0]) if p else None, peak_m=f"{p[1][0]}{p[1][1]:02d}" if p else None,
                        trough_10k=round(t[0]) if t else None, trough_m=f"{t[1][0]}{t[1][1]:02d}" if t else None,
                        p20_10k=round(median(q120[k])) if q120.get(k) else None))
    return sorted(out, key=lambda r: (r["apt_seq"], r["area_group"]))


def region_months(rows: list[dict]) -> list[dict]:
    g: dict[tuple[str, str], dict] = defaultdict(lambda: {"n_all": 0, "n_broker": 0, "n_direct": 0, "n_cancelled": 0, "p84": []})
    for r in rows:
        x = g[(r["region_code"], r["contract_month"])]
        x["n_all"] += 1
        if r["is_cancelled"] in ("1", "True", "true", "t"):
            x["n_cancelled"] += 1
            continue
        if r["deal_type"] == "중개":
            x["n_broker"] += 1
            if math.floor(float(r["area_m2"])) in (84, 85):
                x["p84"].append(int(r["price_10k"]))
        else:
            x["n_direct"] += 1
    return [dict(region_code=k[0], contract_month=k[1], n_all=v["n_all"], n_broker=v["n_broker"], n_direct=v["n_direct"],
                 n_cancelled=v["n_cancelled"], p84_median_10k=round(median(v["p84"])) if v["p84"] else None)
            for k, v in sorted(g.items())]
