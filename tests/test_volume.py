from datetime import date

from collector import volume as V


def test_lag_cdf():
    F = V.lag_cdf([0, 1, 1, 3, 99, -1], max_lag=4)
    assert F == [0.25, 0.75, 0.75, 1.0, 1.0]
    assert V.lag_cdf([], max_lag=2) == [0.0, 0.0, 0.0]


def test_weekday_weights():
    w = V.weekday_weights({0: 10, 1: 10, 2: 10, 3: 10, 4: 10, 5: 20, 6: 0})
    assert abs(sum(w) - 7) < 1e-9 and w[5] == 2 * w[0] and w[6] == 0
    assert V.weekday_weights({}) == [1.0] * 7


def test_shares_and_nowcast():
    F = [min(1.0, d / 10) for d in range(61)]          # 10일이면 다 신고
    wk = [1.0] * 7
    s, frac = V.shares("202609", date(2026, 10, 20), F, wk)
    assert s == 1.0 and frac == 1.0                      # 지난달은 모두 10일 넘게 지남
    s, frac = V.shares("202610", date(2026, 10, 6), F, wk)   # 1~5일 계약, 지연 5~1일
    assert abs(s - 0.3) < 1e-9 and abs(frac - 5 / 31) < 1e-9
    lags = [d for d in range(10) for _ in range(30)]
    sb = V.share_boot("202610", date(2026, 10, 6), lags, wk, boot=30)
    x = V.nowcast(150, sb)
    assert x["lo"] <= x["est"] <= x["hi"] and not x["shown"]
    assert x["full"] == round(x["est"] / sb[1])
    assert V.nowcast(10, V.share_boot("202611", date(2026, 10, 6), lags, wk, boot=5)) is None   # 아직 안 온 달


def test_regular_months():
    assert V.regular_months(date(2026, 1, 3)) == ("202601", "202512")
