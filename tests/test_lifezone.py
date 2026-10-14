from collector.lifezone import agreement, cluster, quarter_index, ratio_cv


def _ix(base, drift):
    return {f"2025Q{q}": base * (1 + drift * q) for q in range(1, 5)} | {"2026Q1": base * (1 + drift * 5)}


def test_ratio_cv():
    a, b = _ix(10, 0.05), _ix(5, 0.05)
    assert ratio_cv(a, b) < 1e-9                 # 같은 비율로 움직임
    assert ratio_cv(a, _ix(5, -0.05)) > 0.05
    assert ratio_cv({"2025Q1": 1}, {"2025Q1": 1}) is None


def test_cluster_respects_river_and_size():
    ix = {"A": _ix(10, .05), "B": _ix(12, .05), "C": _ix(9, .05), "D": _ix(10, -.05), "E": _ix(11, .05)}
    adj = [("A", "B", False), ("B", "C", False), ("C", "D", False), ("A", "E", True)]
    g = cluster(list(ix), adj, ix)
    assert g["A"] == g["B"] == g["C"]            # 함께 움직임
    assert g["D"] != g["C"]                       # 반대로 움직임
    assert g["E"] != g["A"]                       # 한강 건너
    g2 = cluster(list(ix), adj, ix, max_size=2)
    assert len({g2["A"], g2["B"], g2["C"]}) == 2


def test_cluster_attaches_no_data_dong():
    ix = {"A": _ix(10, .05), "B": _ix(12, .05)}
    g = cluster(["A", "B", "X"], [("A", "B", False), ("B", "X", False)], ix)
    assert g["X"] == g["A"]


def test_quarter_index_and_agreement():
    ix = quarter_index([("A", "2025Q1", 1.0)] * 3 + [("A", "2025Q2", 2.0)] * 2)
    assert ix == {"A": {"2025Q1": 1.0}}
    adj = [("A", "B", False), ("B", "C", False)]
    m = agreement({"A": 1, "B": 1, "C": 2}, {"A": "x", "B": "x", "C": "x"}, adj)
    assert m["precision"] == 1.0 and m["recall"] == 0.5
