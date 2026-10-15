from collections import Counter

from collector.lifezone import candidate_pairs, merge, pair_f1, ratio_cv, unit_index, unit_of, zone_name


def _ix(base, drift, n=14):
    return {f"Q{q:02d}": base * (1 + drift * q) for q in range(n)}


def test_unit_of():
    assert unit_of("잠실", 600, "11710") == "S:잠실"
    assert unit_of("잠실", 1500, "11710") == "D:11710"
    assert unit_of(None, None, None) is None


def test_ratio_cv_and_unit_index():
    a, b = _ix(10, 0.05), _ix(5, 0.05)
    assert ratio_cv(a, b) < 1e-9                   # 같은 비율로 움직임
    assert ratio_cv(a, _ix(5, -0.03)) > 0.05
    assert ratio_cv(_ix(1, 0, 3), _ix(1, 0, 3)) is None
    prices = {"c1": {"Q1": 100, "Q2": 110, "Q3": 120, "Q4": 130}, "c2": {"Q1": 50, "Q2": 55, "Q3": 60, "Q4": 65},
              "c3": {"Q1": 10}}
    ix = unit_index(prices, {"c1": "U", "c2": "U", "c3": "U"})
    assert set(ix["U"]) == {"Q1", "Q2", "Q3", "Q4"} and ix["U"]["Q4"] > ix["U"]["Q1"]   # c3 은 분기 부족으로 빠짐


def test_candidate_pairs_line_neighbors_and_river():
    st = {"A": {"lat": 37.50, "lng": 127.00, "lines": {"2호선"}}, "B": {"lat": 37.50, "lng": 127.01, "lines": {"2호선"}},
          "C": {"lat": 37.50, "lng": 127.10, "lines": {"2호선"}}, "N": {"lat": 37.53, "lng": 127.00, "lines": {"3호선"}}}
    units = {"S:A": {"adms": Counter({"1": 3}), "side": "남"}, "S:B": {"adms": Counter({"2": 2}), "side": "남"},
             "S:C": {"adms": Counter({"9": 1}), "side": "남"}, "S:N": {"adms": Counter({"3": 1}), "side": "북"},
             "D:1": {"adms": Counter({"1": 1}), "side": "남"}}
    p = candidate_pairs(units, st, [("2", "3")])
    assert ("S:A", "S:B") in p                     # 같은 노선 이웃(약 0.9km)
    assert ("S:A", "S:C") not in p                 # 9km
    assert ("S:B", "S:N") not in p                 # 붙은 동이지만 한강 건너
    assert ("D:1", "S:A") in p                     # 같은 행정동


def test_merge_limits_span_and_size():
    units = {u: {"n": 10, "lat": 37.5, "lng": lng} for u, lng in [("a", 127.000), ("b", 127.010), ("c", 127.020), ("d", 127.030)]}
    scored = [(0.01, "a", "b"), (0.02, "b", "c"), (0.03, "c", "d"), (0.2, "a", "d")]
    g = merge(units, scored, max_span_m=2000)
    assert g["a"] == g["b"] == g["c"] and g["d"] != g["a"]      # a~d 2.6km 라 d 는 따로
    g = merge(units, scored, max_units=2)
    assert g["a"] == g["b"] and g["c"] == g["d"] and g["a"] != g["c"]
    g = merge(units, scored, cv_max=0.015)
    assert g["a"] == g["b"] and g["c"] != g["b"]


def test_pair_f1_and_name():
    group = {"1": "x", "2": "x", "3": "y", "4": "y"}
    ref = {"1": "z", "2": "z", "3": "z", "4": "w"}
    block = {"1": "gu", "2": "gu", "3": "gu", "4": "gu"}
    p, r, f = pair_f1(group, ref, block)
    assert p == 0.5 and abs(r - 1 / 3) < 1e-9
    assert zone_name(["D:111", "S:잠실", "S:석촌"], {"S:잠실": 50, "S:석촌": 20, "D:111": 5}, {"111": "서울특별시 송파구 잠실2동"}) == "잠실·석촌·잠실2동"
