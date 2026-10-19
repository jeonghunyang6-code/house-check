from collector.region_stats import jeonse_state, pop_keep, sentiment_state
from collector.regions import REGIONS
from collector.sources import kosis
from collector.sources.rone import map_regions, region_key


def test_states():
    assert jeonse_state(49.9).startswith("50% 미만") and jeonse_state(60).startswith("50~80%") and jeonse_state(80).startswith("80% 이상")
    assert sentiment_state(94.9) == "하강 국면" and sentiment_state(95) == "보합 국면" and sentiment_state(115) == "상승 국면"


def test_pop_keep():
    assert pop_keep("201912", "202609") and pop_keep("202409", "202609") and not pop_keep("202408", "202609")


def test_region_key():
    names = ["서울>강북지역>도심권>종로구", "경기>경부1권>안양시>만안구", "인천>영종구", "경기>경부1권>안양시"]
    sgg = map_regions(names, REGIONS)
    assert region_key("서울>강북지역>도심권>종로구", sgg) == "11110"
    assert region_key("경기>경부1권>안양시>만안구", sgg) == "41171"
    assert region_key("경기>경부1권>안양시", sgg) is None
    assert region_key("수도권>서울", sgg) == "11" and region_key("수도권>소계", sgg) == "SUDO" and region_key("전국>소계", sgg) == "KR"
    assert region_key("서울", sgg) == "11" and region_key("부산>중구", sgg) is None


def test_fetch_population(monkeypatch):
    rows = [{"PRD_DE": "202609", "C2_NM": n, "DT": v} for n, v in
            (("계", "1000"), ("0 - 4세", "50"), ("5 - 9세", "60"), ("10 - 14세", "70"), ("15 - 19세", "80"), ("60 - 64세", "90"), ("65 - 69세", "100"), ("100+", "5"))]
    monkeypatch.setattr(kosis, "_call", lambda p: rows)
    assert kosis.fetch_population("11710", "202609", "202609") == {"202609": {"total": 1000, "school": 210, "working": 170, "old": 105}}
