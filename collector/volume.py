"""C1 신고 지연 보정 거래량 (docs/insights/indicators.md C1, ARCHITECTURE 4.2).

실거래는 계약 뒤 30일 안에 신고하면 되므로 최근 1~2개월 거래량은 덜 잡힌다. 국토부 자료에 신고일이 없어
deals.first_seen_date(우리가 처음 받은 날, 2026-10-12~)로 '계약일 → 처음 보인 날' 지연을 잰다.

설계 4.2 의 '과거 12개월 평균 d일차 누적/최종치'는 달마다 처음부터 끝까지 지켜본 기록이 몇 달 쌓여야 한다.
그 전에는 최근 몇 주 동안 새로 보인 거래의 지연 분포(F)로 추정한다: 계약이 날마다 비슷하게 일어난다면
'지연 d일 이하 비율'이 계약 d일 뒤까지 신고된 비율과 같다. 계약 요일 차이(주말에 적음)는 요일 가중치로 넣는다.
"""

from __future__ import annotations

import calendar
import random
from datetime import date, timedelta

MAX_LAG = 60          # 이보다 늦은 신고는 버린다(매일 수집은 당월·전월만 받아 그 밖은 잘 안 보인다)
MIN_LAGS = 1000       # 지연 표본이 이보다 적으면 추정하지 않는다
MIN_DAYS = 7          # 지연을 모은 수집일 수
BOOT = 200
# 🔧 화면에 보정치를 보이는 최소 '보인 비율'. 2026-10-12~18 한 주 자료로 며칠 뒤 건수를 맞혀 보니 전월(보인 비율 95% 안팎)은
# 오차 ±2%, 당월(50~60%)은 −7~−38% 라 당월 추정은 아직 못 믿는다. 자료가 쌓이면 actual 로 다시 정한다
SHOW_SHARE = 0.8


def lag_cdf(lags: list[int], max_lag: int = MAX_LAG) -> list[float]:
    """F[d] = 지연 d일 이하 비율 (d = 0..max_lag). 지연이 max_lag 를 넘거나 음수인 것은 뺀다."""
    cnt = [0] * (max_lag + 1)
    for x in lags:
        if 0 <= x <= max_lag:
            cnt[x] += 1
    tot = sum(cnt)
    if not tot:
        return [0.0] * (max_lag + 1)
    out, acc = [], 0
    for c in cnt:
        acc += c
        out.append(acc / tot)
    return out


def weekday_weights(counts: dict[int, int]) -> list[float]:
    """요일(0=월)별 계약 건수 → 평균 1 인 가중치. 자료가 없으면 모두 1."""
    vals = [counts.get(i, 0) for i in range(7)]
    m = sum(vals) / 7
    return [v / m for v in vals] if m else [1.0] * 7


def month_days(month: str) -> list[date]:
    y, m = int(month[:4]), int(month[4:])
    return [date(y, m, d) for d in range(1, calendar.monthrange(y, m)[1] + 1)]


def shares(month: str, today: date, F: list[float], wk: list[float]) -> tuple[float, float]:
    """(지금까지 계약된 것 중 지금 보이는 비율, 한 달 전체 중 지금까지 계약된 비율). 계약은 어제까지만 센다."""
    days = month_days(month)
    seen = [d for d in days if d < today]
    tot = sum(wk[d.weekday()] for d in days)
    w = sum(wk[d.weekday()] for d in seen)
    if not w:
        return 0.0, 0.0
    last = len(F) - 1
    s = sum(wk[d.weekday()] * F[min((today - d).days, last)] for d in seen) / w
    return s, w / tot


def share_boot(month: str, today: date, lags: list[int], wk: list[float], boot: int = BOOT, seed: int = 0) -> tuple[float, float, list[float]]:
    """(보이는 비율, 한 달 중 지난 비율, 지연 표본을 boot 번 다시 뽑아 본 보이는 비율들). 지역마다 같으니 달마다 한 번만 계산한다."""
    s, frac = shares(month, today, lag_cdf(lags), wk)
    rng = random.Random(seed)
    bs = [shares(month, today, lag_cdf(rng.choices(lags, k=len(lags))), wk)[0] for _ in range(boot)] if s > 0 else []
    return s, frac, sorted(b for b in bs if b > 0)


def nowcast(observed: int, sb: tuple[float, float, list[float]]) -> dict | None:
    """신고 지연을 감안한 거래량 추정. est = 지금까지 계약된 거래, full = 그 달 전체(달이 안 끝났으면 요일 가중으로 늘림).
    lo·hi 는 지연 표본 재추출 10~90% 범위 — 표본 잡음만 담고 '계약이 날마다 비슷' 가정의 오차는 담지 않는다."""
    s, frac, bs = sb
    if s <= 0:
        return None
    est = observed / s
    lo = round(observed / bs[len(bs) * 9 // 10]) if bs else None   # 보이는 비율이 클수록 추정은 작다
    hi = round(observed / bs[len(bs) // 10]) if bs else None
    return dict(share=s, month_frac=frac, est=round(est), lo=lo, hi=hi, full=round(est / frac) if frac else None,
                shown=s >= SHOW_SHARE)


def regular_months(seen: date) -> tuple[str, str]:
    """그날 정기 수집이 받은 달(당월·전월). 해제 재확인으로 받은 옛 달의 first_seen 은 신고일과 무관해 지연에서 뺀다."""
    prev = seen.replace(day=1) - timedelta(days=1)
    return seen.strftime("%Y%m"), prev.strftime("%Y%m")
