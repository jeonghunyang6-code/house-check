"""시장 국면·체크리스트 계산 (순수 함수). 정의: docs/insights/indicators.md

- B1 국면: 월별 값 12개월 누적 변화와 월별 방향 일관성 (📖 추세 최소 1년, 단기 3개월 p.136 / 🔧 ±3%, 8개월)
- B3 낙폭: 최근 24개월 최고 대비 현재 (📖 5~10% 단기 조정, 20% p.434·444)
- B4 하락 분류: ① 전국 하락 지역 비율 4주 평균 ≥ 70% ② 수도권 전세 8주 연속 하락 ③ 실업률 (📖 p.435~436 / 🔧 70%, 8주)
- B5 ① 상승 지역 비율
- 반등 신호: 매매수급지수 상승 전환 (3절). 🔧 4주 연속 상승을 "전환"으로 본다
- D5 신규 전세 감소 + 전세가 상승 = 전세 부족 → 매매 상승 압력 (▶ J5 / 🔧 최근 신고 완료 3개월 신규 전세 건수 전년 같은 달 대비 감소, 전세지수 13주 상승)
- G1 유동성·소득·집값: 2005 = 100 재기준화 (📖 p.50)
- G2 금리와 집값: 기준금리 12개월 변화와 아파트값 전년비가 같은 방향이면 동행, 반대면 역행 (📖 p.48~49 "금리는 집값을 조절하지 않는다")
- G3 주담대 금리 구간 (▶ 3~5% 심리적 한계, 7%면 체감이 완전히 다르다)
- G4 가계대출 증가율: 잔액 전년비와 3개월 전 대비 변화 (▶ 증가율 둔화 → 거래 감소 / 🔧 3개월 변화 < 0 이면 둔화)
- G5 실업률 구간과 B4 ③ (📖 4% 경기침체·6% 경제 위기 p.143~144 / 🔧 3개월 +0.5%p)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

UP_MIN = 3.0       # 🔧 12개월 누적 ±3%
CONSIST = 8        # 🔧 12개월 중 8개월
DOWN_RATIO = 70.0  # 🔧 하락 지역 비율 70%
JEONSE_WEEKS = 8   # 🔧 전세 8주 연속 하락
SUPPLY_WEEKS = 4   # 🔧 수급지수 4주 연속 상승 = 상승 전환
UNEMP_RECESSION = 4.0  # 📖 실업률 4% 접근 = 경기침체 (p.143~144)
UNEMP_CRISIS = 6.0     # 📖 6% 이상 = 경제 위기
UNEMP_JUMP = 0.5       # 🔧 3개월 사이 +0.5%p 이상 오르면 B4 ③ 충족
RATE_BANDS = (3.0, 5.0, 7.0)  # ▶ 주담대 금리 3~5% 심리적 한계, 7%


def monthly(points: list[tuple[date, float]]) -> list[tuple[str, float]]:
    """주간 (날짜, 지수) → 월별 (YYYYMM, 그 달 마지막 주 값). 마지막 달은 최신 주 값."""
    out: dict[str, float] = {}
    for d, v in sorted(points):
        out[d.strftime("%Y%m")] = v
    return sorted(out.items())


@dataclass(frozen=True)
class Phase:
    chg_12m: float | None
    up_months: int | None
    down_months: int | None
    last3: str | None
    phase: str | None
    drawdown: float | None


def phase(months: list[tuple[str, float]]) -> Phase:
    """월별 값(오래된 것부터) → B1 국면 + B3 낙폭. 13개월(12개 변화) 미만이면 판정하지 않는다."""
    vals = [v for _, v in months]
    dd = None
    if vals:
        recent = vals[-25:]
        hi = max(recent)
        dd = round((hi - vals[-1]) / hi * 100, 2) if hi else None
    if len(vals) < 13:
        return Phase(None, None, None, None, None, dd)
    last13 = vals[-13:]
    diffs = [b - a for a, b in zip(last13, last13[1:])]
    chg = (last13[-1] / last13[0] - 1) * 100
    up = sum(d > 0 for d in diffs)
    down = sum(d < 0 for d in diffs)
    l3 = diffs[-3:]
    last3 = "상승" if all(d > 0 for d in l3) else "하락" if all(d < 0 for d in l3) else "혼조"
    if chg >= UP_MIN and up >= CONSIST:
        p = "상승장"
    elif chg <= -UP_MIN and down >= CONSIST:
        p = "하락장"
    elif abs(chg) < UP_MIN:
        p = "보합장"
    elif last3 == "상승":
        p = "일시 반등"
    elif last3 == "하락":
        p = "일시 조정"
    else:
        p = "추세 불명확"
    return Phase(round(chg, 2), up, down, last3, p, dd)


# 여러 시도를 묶은 집계 이름 (2026-10-05 주 응답에서 확인). 세종처럼 하위가 없는 시도는 말단 지역으로 센다.
AGGREGATES = {"전국", "수도권", "지방권", "4대광역시", "5대광역시", "7개도", "8개도"}


def breadth(cur: dict[str, float], prev: dict[str, float]) -> tuple[int, int, int]:
    """한 주의 지역별 지수(경로 → 값)와 직전 주 → (말단 지역 수, 상승, 하락).
    말단 = 다른 지역의 상위가 아니고 묶음 집계도 아닌 지역 (2026-10-05 주 전국 189곳)."""
    names = [k for k in cur if k in prev]
    parents = {n.rsplit(">", 1)[0] for n in names if ">" in n}
    leaves = [n for n in names if n not in parents and n not in AGGREGATES]
    up = sum(cur[n] > prev[n] for n in leaves)
    down = sum(cur[n] < prev[n] for n in leaves)
    return len(leaves), up, down


def run_length(values: list[float], direction: int) -> int:
    """끝에서부터 같은 방향(+1 상승, -1 하락)으로 움직인 주 수."""
    n = 0
    for a, b in zip(values[-2::-1], values[::-1]):
        if (b - a) * direction > 0:
            n += 1
        else:
            break
    return n


def b4(down_ratio_4w: float | None, jeonse_down_weeks: int | None, unemployment_met: bool | None) -> tuple[int, int, str]:
    """B4 조건 → (충족 수, 판단 가능한 조건 수, 분류). 둘 이상 충족이면 대세 하락 의심."""
    conds = [
        None if down_ratio_4w is None else down_ratio_4w >= DOWN_RATIO,
        None if jeonse_down_weeks is None else jeonse_down_weeks >= JEONSE_WEEKS,
        unemployment_met,
    ]
    met = sum(c is True for c in conds)
    known = sum(c is not None for c in conds)
    return met, known, "대세 하락 의심" if met >= 2 else "단기 조정"


@dataclass(frozen=True)
class Unemployment:
    period: str
    rate: float
    chg_3m: float | None   # 3개월 전 대비 %p
    band: str              # 안정 | 경기침체 | 경제 위기
    b4_met: bool           # B4 ③: 4% 이상 또는 3개월 +0.5%p 이상


def unemployment(months: list[tuple[str, float]]) -> Unemployment | None:
    """월별 계절조정 실업률(오래된 것부터) → G5 구간과 B4 ③."""
    if not months:
        return None
    period, rate = months[-1]
    chg = round(rate - months[-4][1], 2) if len(months) >= 4 else None
    band = "경제 위기" if rate >= UNEMP_CRISIS else "경기침체" if rate >= UNEMP_RECESSION else "안정"
    met = rate >= UNEMP_RECESSION or (chg is not None and chg >= UNEMP_JUMP)
    return Unemployment(period, rate, chg, band, met)


def mortgage_band(rate: float) -> str:
    """G3 주담대 금리(신규취급) 구간."""
    lo, hi, shock = RATE_BANDS
    if rate >= shock:
        return "7% 이상 (체감 급변)"
    if rate >= hi:
        return "5~7% (한계 초과)"
    if rate >= lo:
        return "3~5% (심리적 한계 구간)"
    return "3% 미만"


@dataclass(frozen=True)
class LoanGrowth:
    period: str
    yoy: float               # 잔액 전년 동월 대비 %
    yoy_chg_3m: float | None  # 3개월 전 전년비 대비 %p
    state: str               # 둔화 | 확대 | 비교 불가


def loan_growth(months: list[tuple[str, float]]) -> LoanGrowth | None:
    """월말 잔액(오래된 것부터, 빠진 달 없음 가정) → G4. 13개월 미만이면 None."""
    if len(months) < 13:
        return None
    vals = [v for _, v in months]

    def yoy(i: int) -> float:
        return (vals[i] / vals[i - 12] - 1) * 100

    now = yoy(len(vals) - 1)
    chg = round(now - yoy(len(vals) - 4), 2) if len(vals) >= 16 else None
    state = "비교 불가" if chg is None else "둔화" if chg < 0 else "확대" if chg > 0 else "유지"
    return LoanGrowth(months[-1][0], round(now, 2), chg, state)


G1_BASE = "2005"  # 📖 p.50 그래프의 기준 연도


def rebase(points: list[tuple[str, float]], base: str = G1_BASE) -> list[tuple[str, float]]:
    """(YYYY 또는 YYYYMM, 값) → 기준 연도 = 100. 월간은 기준 연도 평균, 연간은 그 해 값으로 나눈다. 기준 연도 값이 없으면 빈 목록."""
    b = [v for p, v in points if p[:4] == base]
    if not b:
        return []
    m = sum(b) / len(b)
    return [(p, round(v / m * 100, 1)) for p, v in points if p[:4] >= base]


@dataclass(frozen=True)
class NewJeonse:
    months: tuple[str, ...]   # 비교한 최근 3개월 (신고 기한이 지난 달)
    n_new: int                # 그 3개월 신규 전세 건수
    n_new_prev: int           # 1년 전 같은 3개월
    yoy: float | None         # %
    renew_share: float | None  # 갱신 / (신규 + 갱신) %
    jeonse_chg: float | None  # 전세지수 13주 변화 %
    state: str                # 충족 | 미충족 | 데이터 없음


def _shift(ym: str, k: int) -> str:
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 + k, 12)
    return f"{y}{m + 1:02d}"


def new_jeonse(counts: dict[str, tuple[int, int]], last_complete: str, jeonse_chg: float | None) -> NewJeonse:
    """counts: 계약월 → (신규 전세, 갱신 전세). last_complete: 신고 기한(30일)이 지나 다 모인 마지막 달.
    계약구분 필드는 2021-06부터 채워진다(그 전은 대부분 공백)."""
    ms = tuple(_shift(last_complete, -k) for k in (2, 1, 0))
    prev = [_shift(m, -12) for m in ms]
    if not all(m in counts for m in ms + tuple(prev)) or min(ms + tuple(prev)) < "202106":
        return NewJeonse(ms, 0, 0, None, None, jeonse_chg, "데이터 없음")
    n = sum(counts[m][0] for m in ms)
    n0 = sum(counts[m][0] for m in prev)
    r = sum(counts[m][1] for m in ms)
    yoy = round((n / n0 - 1) * 100, 1) if n0 else None
    share = round(r / (n + r) * 100, 1) if n + r else None
    if yoy is None or jeonse_chg is None:
        state = "데이터 없음"
    else:
        state = "충족" if yoy < 0 and jeonse_chg > 0 else "미충족"
    return NewJeonse(ms, n, n0, yoy, share, jeonse_chg, state)



def yoy_series(months: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """월별 값 → 전년 같은 달 대비 % (12개월 전 값이 있는 달만)."""
    d = dict(months)
    return [(p, round((v / d[_shift(p, -12)] - 1) * 100, 2)) for p, v in months if _shift(p, -12) in d and d[_shift(p, -12)]]


def rate_price_relation(rate: list[tuple[str, float]], price: list[tuple[str, float]]) -> list[tuple[str, str]]:
    """G2: 달마다 기준금리 12개월 변화 방향과 아파트값 전년비 방향 → 동행 | 역행 | 금리 동결.
    인상기(+)·상승(+) 또는 인하기(-)·하락(-)이면 동행. 금리가 1년 전과 같으면 금리 동결."""
    r = dict(rate)
    out = []
    for p, py in yoy_series(price):
        prev = _shift(p, -12)
        if p not in r or prev not in r:
            continue
        dr = r[p] - r[prev]
        if abs(dr) < 1e-9:
            out.append((p, "금리 동결"))
        elif py == 0:
            continue
        else:
            out.append((p, "동행" if (dr > 0) == (py > 0) else "역행"))
    return out
