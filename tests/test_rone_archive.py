from jobs import rone_archive as R


def test_merged_new_wins_and_sorted():
    old = [{"stat": "sale", "cls_id": "11", "week_id": "201201", "week_date": "2012-01-02", "value": "1"},
           {"stat": "sale", "cls_id": "2", "week_id": "201201", "week_date": "2012-01-02", "value": "5"}]
    new = [{"stat": "sale", "cls_id": 11, "week_id": "201201", "week_date": "2012-01-02", "value": 2.0}]
    m = R.merged(old, new)
    assert [r["cls_id"] for r in m] == ["2", 11] and m[1]["value"] == 2.0


def test_where_keeps_capital_series():
    assert "50008" in R.WHERE and "50002" in R.WHERE and "2020-01-01" in R.WHERE
