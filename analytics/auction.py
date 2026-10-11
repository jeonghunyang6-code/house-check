"""경매 매각가율·매각률 계산 (지표 G6).

입력은 월별·지역별·용도별 집계값이다. 데이터 출처(감평협회 파일, 지지옥션 보도)와 무관하게
같은 함수로 계산하도록 순수 함수로만 구성한다.

주의: 매각가율은 **매각된 물건의 감정 금액**을 분모로 해야 한다. 경매에 나온 전체 물건의 감정 금액을
분모로 쓰면 유찰 물건이 섞여 낮게 나온다. 원천 데이터의 감정 금액 기준을 먼저 확인할 것.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonthlyAuction:
    month: str  # "YYYY-MM"
    cases: int  # 경매 건수
    sold: int  # 매각 건수
    appraisal_of_sold: int  # 매각 물건의 감정 금액 (원)
    sale_amount: int  # 매각 금액 (원)


def sale_ratio(sale_amount: int, appraisal_of_sold: int) -> float | None:
    """매각가율 = 매각 금액 ÷ 매각 물건의 감정 금액. 매각 건이 없으면 None."""
    if appraisal_of_sold <= 0:
        return None
    return sale_amount / appraisal_of_sold


def sold_ratio(sold: int, cases: int) -> float | None:
    """매각률 = 매각 건수 ÷ 경매 건수."""
    if cases <= 0:
        return None
    return sold / cases


def rolling_sale_ratio(rows: list[MonthlyAuction], months: int = 12) -> list[tuple[str, float | None]]:
    """직전 `months`개월 **합계 기준** 매각가율.

    월별 비율의 평균이 아니라 금액 합계끼리 나눈다. 건수가 많은 달에 가중치가 실리고,
    매각 건수가 적은 달의 극단값이 평균을 왜곡하지 않는다.
    """
    ordered = sorted(rows, key=lambda r: r.month)
    out: list[tuple[str, float | None]] = []
    for i, row in enumerate(ordered):
        if i + 1 < months:
            out.append((row.month, None))  # 창이 다 차기 전에는 계산하지 않는다
            continue
        window = ordered[i + 1 - months : i + 1]
        out.append((row.month, sale_ratio(sum(r.sale_amount for r in window),
                                          sum(r.appraisal_of_sold for r in window))))
    return out
