from collector.deal_anchor import anchors, region_months


def _r(d, p, area="84.9", t="중개", c="0", seq="11-1"):
    return {"apt_seq": seq, "area_m2": area, "contract_date": d, "contract_month": d[:4] + d[5:7], "price_10k": str(p),
            "deal_type": t, "is_cancelled": c, "region_code": "11680"}


def test_anchors_peak_trough_hist_p20():
    rows = [_r("2020-02-01", 50000), _r("2020-03-01", 60000),
            _r("2021-09-10", 100000), _r("2021-10-10", 120000),   # 3개월 창: 2021-10·11 = 110000, 2021-12 = 120000
            _r("2022-12-01", 80000),                               # 2022-12~2023-02 ref 80000
            _r("2023-03-01", 90000),
            _r("2021-11-01", 999999, t="직거래"), _r("2021-11-02", 888888, c="1")]
    a = anchors(rows)
    assert len(a) == 1
    x = a[0]
    assert x["area_group"] == 84 and x["hist_high_10k"] == 120000 and x["hist_high_date"] == "2021-10-10"
    assert x["peak_10k"] == 120000 and x["peak_m"] == "202112"
    assert x["trough_10k"] == 80000 and x["trough_m"] == "202212"
    assert x["p20_10k"] == 55000


def test_region_months():
    rows = [_r("2020-01-05", 100), _r("2020-01-06", 300, area="85.0"), _r("2020-01-07", 900, area="59.9"),
            _r("2020-01-08", 50, t="직거래"), _r("2020-01-09", 70, c="1")]
    sido, m = region_months(rows)
    assert sido["region_code"] == "11" and sido["n_all"] == 5
    assert (m["n_all"], m["n_broker"], m["n_direct"], m["n_cancelled"], m["p84_median_10k"]) == (5, 3, 1, 1, 200)
