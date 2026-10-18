"""지역 월별 지표의 판정 (jobs/region_stats.py, 0045). 순수 함수.

- D1 지역 평균 전세가율 (▶ 요즘 전세가는 거품인가 3:55, 너무 빨리 오르고 있어요 3:49 / 📖 p.151):
  시장 평균 60% 가 균형, 50% 이하면 투자 수요가 들어오기 어렵고, 80~90% 는 조심
- G7 소비심리지수 (국토연구원 정의: 95 미만 하강, 95~115 보합, 115 이상 상승 국면). 📖 심리는 객관성에 한계가 있어 보조로만 p.51~52
- 인구: 해마다 12월 값과 최근 25개월만 남긴다(5년 변화·최근 추이에 충분)
"""

from __future__ import annotations


def jeonse_state(v: float | None) -> str:
    if v is None:
        return "데이터 없음"
    if v < 50:
        return "50% 미만(투자 수요 유입 어려움)"
    if v >= 80:
        return "80% 이상(조심)"
    return "50~80%(60% 균형 부근)"


def sentiment_state(v: float | None) -> str:
    if v is None:
        return "데이터 없음"
    return "하강 국면" if v < 95 else "상승 국면" if v >= 115 else "보합 국면"


def ym_add(ym: str, k: int) -> str:
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 + k, 12)
    return f"{y}{m + 1:02d}"


def pop_keep(period: str, latest: str, recent: int = 25) -> bool:
    return period.endswith("12") or period > ym_add(latest, -recent)
