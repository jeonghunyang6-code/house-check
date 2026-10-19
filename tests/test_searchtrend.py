from collector.searchtrend import ANCHOR, body, index, keywords


def test_keywords():
    assert keywords("은마", "대치동") == ["은마", "은마아파트", "대치은마"]
    assert keywords("헬리오시티", "가락동") == ["헬리오시티", "헬리오시티아파트", "가락헬리오시티"]
    assert keywords("우성2차", "개포동") == ["개포우성2차", "개포우성2차아파트"]       # 흔한 이름은 동 이름 붙인 것만
    assert keywords("현대(2-4차)", "오금동") == ["오금현대", "오금현대아파트"]
    assert keywords("대치우성", "대치동") == ["대치우성", "대치우성아파트"]
    assert keywords("e", "x동") is None and keywords("현대", None) is None
    assert keywords("남산타운", "신당동", ("신당남산타운(분양)",)) == ["남산타운", "남산타운아파트", "신당남산타운", "신당남산타운아파트"]


def test_aliases():
    from collector.searchtrend import aliases
    assert aliases("목동신시가지7", "목") == ["목동7단지", "목동신시가지7단지", "목동신시가지7차"]
    assert aliases("주공17단지", "창") == ["주공17단지", "창주공17단지"]
    assert aliases("산내마을9단지힐스테이트운정", "목") == ["산내마을9단지", "산내9단지"]
    assert aliases("헬리오시티", "가락") == []


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
