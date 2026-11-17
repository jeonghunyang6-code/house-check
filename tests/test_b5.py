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
    z = dict(n_g7=0, h_g7=0, n_g8=0, h_g8=0)
    assert m["202101"] == dict(n_low=2, h_low=2, n_top=1, h_top=0, n_lip=2, h_lip=2, **z)
    assert m["202102"] == dict(n_low=1, h_low=0, n_top=0, h_top=0, n_lip=1, h_lip=0, **z)


def test_monthly_gyeonggi_7_8():
    """C11: 경기(41) 7·8급만 따로. 서울 8급은 안 셈."""
    cx = {"G8": {"grade": 8, "region_code": "41390", "build_year": 2005, "households": 900},
          "G7": {"grade": 7, "region_code": "41450", "build_year": 2010, "households": 900},
          "S8": {"grade": 8, "region_code": "11350", "build_year": 1990, "households": 900}}
    rows = [_r("G8", "2020-12-01", 100), _r("G8", "2021-01-02", 101), _r("G7", "2020-12-01", 200), _r("G7", "2021-01-03", 150),
            _r("S8", "2020-12-01", 100), _r("S8", "2021-01-04", 120)]
    o = monthly(rows, cx)["202101"]
    assert (o["n_g8"], o["h_g8"], o["n_g7"], o["h_g7"]) == (1, 1, 1, 0) and o["n_low"] == 3
