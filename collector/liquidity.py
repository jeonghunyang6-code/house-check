"""C3 하락기 환금성·C4 거래 유지율 (docs/insights/indicators.md C3·C4, 0041).

📖 "하락장에 거래가 많았던 단지 = 환금성이 좋다" p.138~142, 하락장에 거래가 끊긴 단지 p.140 그래프 / ▶ V4.
- 하락 구간: 지역 R-ONE 주간 매매지수의 2021-01~2022-12 최고 주 → 그 뒤 2023-12 까지 최저 주. 시군구 시계열이
  2021-01 전부터 없으면(인천 신설 구·화성 구 등) 시도 구간을 쓴다
- C3 = 하락 구간(고점 다음 달 ~ 저점 달) 단지 월평균 거래(중개·비해제) ÷ 세대수 × 100. 같은 시군구 안 분위
- C4 = C3 ÷ 상승 구간(2020-01 ~ 고점 달) 회전율. 거래가 얼마나 남았나. 같은 시군구 안 분위
- 직거래는 뺀다: 하락기에 가족 간 거래가 늘어(📖 p.404) 환금성처럼 보이기 때문. (C2 는 직거래 포함)
- 작가 기준선이 없어 판정 없이 값과 지역 안 분위만 둔다
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

UP_START = "202001"            # 보관 파일 시작 = 상승 구간 시작
PEAK_FROM, PEAK_TO = date(2021, 1, 1), date(2022, 12, 31)
TROUGH_TO = date(2023, 12, 31)
SERIES_FROM = date(2021, 1, 31)   # 시계열이 이 날 전부터 있어야 고점을 찾을 수 있다
SETTLE_MONTHS = 36             # 🔧 사용승인이 구간 시작 36개월 전보다 늦으면 뺀다. 입주 초기엔 거래가 적다가 2년 보유 뒤 매도가
                               # 몰린다: 서울 C4 중앙값 2016년 이전 입주 0.17~0.30, 2017년 0.37, 2018년 0.43, 2019년 0.81 (2026-10-18)
MIN_REGION = 5                 # 🔧 지역 안 분위는 단지 5곳 이상일 때만
SIDO = ("11", "28", "41")


@dataclass(frozen=True)
class Window:
    peak_m: str                # YYYYMM, 상승 구간 끝 / 하락 구간 시작 직전
    trough_m: str              # YYYYMM, 하락 구간 끝
    drop_pct: float            # 고점 대비 저점 지수 변화 (%)
    source: str                # 'sgg' | 'sido'


def ym(d: date) -> str:
    return f"{d.year}{d.month:02d}"


def months_between(a: str, b: str) -> int:
    """a < m <= b 인 달 수."""
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[4:]) - int(a[4:])


def shift(m: str, k: int) -> str:
    y, mm = divmod(int(m[:4]) * 12 + int(m[4:]) - 1 + k, 12)
    return f"{y}{mm + 1:02d}"


def decline_window(series: list[tuple[date, float]], source: str = "sgg") -> Window | None:
    """series: (주 날짜, 매매지수). 2021-01 전부터 이어지지 않으면 None."""
    s = sorted(series)
    if not s or s[0][0] > SERIES_FROM:
        return None
    pk = [(d, v) for d, v in s if PEAK_FROM <= d <= PEAK_TO]
    if not pk:
        return None
    pd_, pv = max(pk, key=lambda t: (t[1], -t[0].toordinal()))   # 같으면 이른 주
    tr = [(d, v) for d, v in s if pd_ < d <= TROUGH_TO]
    if not tr:
        return None
    td, tv = min(tr, key=lambda t: (t[1], t[0]))
    if ym(td) <= ym(pd_):
        return None
    return Window(ym(pd_), ym(td), round((tv / pv - 1) * 100, 2), source)


def region_windows(series_by_region: dict[str, list[tuple[date, float]]]) -> dict[str, Window]:
    """키: 시군구 코드(5자리) 또는 시도 코드(2자리). 시군구 구간이 없으면 시도 구간으로 채운다."""
    out = {}
    for rc, s in series_by_region.items():
        w = decline_window(s, "sido" if len(rc) == 2 else "sgg")
        if w:
            out[rc] = w
    return out


def window_for(windows: dict[str, Window], region_code: str) -> Window | None:
    return windows.get(region_code) or windows.get(region_code[:2])


@dataclass(frozen=True)
class Info:
    region_code: str
    households: int
    use_date: date | None


def _is_cancelled(v: str) -> bool:
    return v in ("1", "True", "true", "t")


def _pct_rank(vals: dict[str, float]) -> dict[str, float | None]:
    """낮을수록 0, 높을수록 100. 같은 값은 같은 분위(아래쪽)."""
    if len(vals) < MIN_REGION:
        return {k: None for k in vals}
    xs = sorted(vals.values())
    n = len(xs)
    out = {}
    for k, v in vals.items():
        below = sum(1 for x in xs if x < v)
        out[k] = round(below * 100 / (n - 1), 1)
    return out


def liquidity(rows: Iterable[dict], windows: dict[str, Window], info: dict[str, Info]) -> list[dict]:
    """rows: 보관 파일 decode 결과(2020-01~ 저점 달까지). info: apt_seq → 세대수·사용승인일 (K-apt 연결 단지만).
    거래가 0건인 단지도 info 에 있으면 회전율 0 으로 넣는다(거래가 끊긴 단지가 바로 찾으려는 것)."""
    cnt_up: dict[str, int] = {}
    cnt_dn: dict[str, int] = {}
    for r in rows:
        if _is_cancelled(r["is_cancelled"]) or r["deal_type"] != "중개":
            continue
        x = info.get(r["apt_seq"])
        w = window_for(windows, x.region_code) if x else None
        if not w:
            continue
        m = r["contract_month"]
        if UP_START <= m <= w.peak_m:
            cnt_up[r["apt_seq"]] = cnt_up.get(r["apt_seq"], 0) + 1
        elif w.peak_m < m <= w.trough_m:
            cnt_dn[r["apt_seq"]] = cnt_dn.get(r["apt_seq"], 0) + 1

    out: dict[str, dict] = {}
    for seq, x in info.items():
        w = window_for(windows, x.region_code)
        if not w or x.households <= 0:
            continue
        if x.use_date and ym(x.use_date) > shift(w.peak_m, -SETTLE_MONTHS):
            continue
        n_dn_m = months_between(w.peak_m, w.trough_m)
        n_up_m = months_between(shift(UP_START, -1), w.peak_m)
        dn = cnt_dn.get(seq, 0) / n_dn_m * 100 / x.households
        up = cnt_up.get(seq, 0) / n_up_m * 100 / x.households
        # C4 는 상승 구간 시작에 이미 자리 잡은 단지만(사용승인이 2020-01 의 SETTLE_MONTHS 전보다 늦으면 빼고 C3 만)
        old_enough = not x.use_date or ym(x.use_date) <= shift(UP_START, -SETTLE_MONTHS)
        out[seq] = dict(apt_seq=seq, region_code=x.region_code, households=x.households,
                        peak_m=w.peak_m, trough_m=w.trough_m, drop_pct=w.drop_pct, window_src=w.source,
                        down_n=cnt_dn.get(seq, 0), down_turnover=round(dn, 3),
                        up_n=cnt_up.get(seq, 0) if old_enough else None,
                        up_turnover=round(up, 3) if old_enough else None,
                        keep_ratio=round(dn / up, 3) if old_enough and up > 0 else None)

    by_region: dict[str, dict[str, dict]] = {}
    for seq, o in out.items():
        by_region.setdefault(o["region_code"], {})[seq] = o
    for grp in by_region.values():
        r3 = _pct_rank({k: o["down_turnover"] for k, o in grp.items()})
        r4 = _pct_rank({k: o["keep_ratio"] for k, o in grp.items() if o["keep_ratio"] is not None})
        for k, o in grp.items():
            o["down_rank"] = r3[k]
            o["keep_rank"] = r4.get(k)
    return sorted(out.values(), key=lambda o: o["apt_seq"])
