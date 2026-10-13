from collector.b5 import monthly


def _r(seq, d, p, t="중개", c="0", area="84.9"):
    return {"apt_seq": seq, "contract_date": d, "price_10k": str(p), "deal_type": t, "is_cancelled": c, "area_m2": area}


def test_monthly_new_high_counts():
    cx = {"L": {"grade": 7, "build_year": 1995, "households": 200}, "T": {"grade": 2, "build_year": 2015, "households": 900},
          "M": {"grade": 4, "build_year": 2000, "households": 500}}
    rows = [_r("L", "2020-12-01", 100), _r("L", "2021-01-05", 110), _r("L", "2021-01-05", 105),   # 같은 날: 둘 다 전고점 100 기준 → 둘 다 신고가
            _r("L", "2021-02-01", 108), _r("L", "2021-02-02", 999, t="직거래"),                  # 108 < 110 → 아님, 직거래 무시
            _r("T", "2021-01-10", 300), _r("T", "2021-01-20", 290),                                  # 첫 거래는 전고점 없음 → 제외
            _r("M", "2020-01-01", 1), _r("M", "2021-01-01", 2)]                                      # 중간 급지 제외
    m = monthly(rows, cx)
    assert m["202101"] == dict(n_low=2, h_low=2, n_top=1, h_top=0, n_lip=2, h_lip=2)
    assert m["202102"] == dict(n_low=1, h_low=0, n_top=0, h_top=0, n_lip=1, h_lip=0)
