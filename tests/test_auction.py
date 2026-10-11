from analytics.auction import MonthlyAuction, rolling_sale_ratio, sale_ratio, sold_ratio


def test_sale_ratio_basic():
    # 감정가 10억짜리가 8억 5천에 낙찰 → 85%
    assert sale_ratio(850_000_000, 1_000_000_000) == 0.85


def test_sale_ratio_none_when_nothing_sold():
    assert sale_ratio(0, 0) is None


def test_sold_ratio():
    assert sold_ratio(25, 100) == 0.25
    assert sold_ratio(0, 0) is None


def test_rolling_uses_sums_not_mean_of_ratios():
    # 1월: 감정 100, 매각 100 (100%) / 2월: 감정 900, 매각 450 (50%)
    # 비율 평균이면 75%, 합계 기준이면 550/1000 = 55%
    rows = [
        MonthlyAuction("2026-01", 10, 5, 100, 100),
        MonthlyAuction("2026-02", 90, 45, 900, 450),
    ]
    out = dict(rolling_sale_ratio(rows, months=2))
    assert out["2026-01"] is None  # 창이 덜 찬 달
    assert out["2026-02"] == 0.55


def test_rolling_sorts_input():
    rows = [
        MonthlyAuction("2026-02", 1, 1, 100, 90),
        MonthlyAuction("2026-01", 1, 1, 100, 80),
    ]
    assert dict(rolling_sale_ratio(rows, months=1)) == {"2026-01": 0.8, "2026-02": 0.9}
