from collector.searchtrend import ANCHOR, body, index, keyword


def test_keyword():
    assert keyword("은마", "대치동") == "대치은마"            # 두 글자는 동 이름을 붙인다
    assert keyword("헬리오시티", "가락동") == "헬리오시티"
    assert keyword("우성2차", "개포동") == "개포우성2차"
    assert keyword("현대(2-4차)", "오금동") == "오금현대"
    assert keyword("래미안", "성수동1가") == "성수래미안"
    assert keyword("e", "x동") is None


def test_body_and_index():
    b = body("2025-10-01", "2026-09-30", [("A", ["대치은마"]), ("B", ["개포우성2차"])])
    assert b["keywordGroups"][0]["groupName"] == ANCHOR[0] and len(b["keywordGroups"]) == 3
    resp = {"results": [{"title": ANCHOR[0], "data": [{"period": "2025-10-01", "ratio": 100}, {"period": "2025-11-01", "ratio": 80}]},
                        {"title": "A", "data": [{"period": "2025-10-01", "ratio": 45}, {"period": "2025-11-01", "ratio": 45}]},
                        {"title": "B", "data": []}]}
    out = index(resp, 2)
    assert out["A"] == {"avg": 45.0, "n": 2, "idx": 0.5} and out["B"] == {"avg": 0.0, "n": 0, "idx": 0.0}


def test_window():
    from datetime import date
    from jobs.searchtrend import window
    assert window(date(2026, 10, 19)) == ("2025-10-01", "2026-09-30")
    assert window(date(2026, 1, 5)) == ("2025-01-01", "2025-12-31")
