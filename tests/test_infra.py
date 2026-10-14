from collector.infra import dist_m, merge_stations, nearest, normalize_station


def test_normalize_station_variants():
    assert normalize_station({"역명": "서울", "위도": "37.55315", "경도": "126.972533", "호선": "1"}) == \
        {"name": "서울", "line": "1호선", "lat": 37.55315, "lng": 126.972533}
    r = normalize_station({"역사명": "검단호수공원역", "역위도": "37.60256", "역경도": "126.688338", "노선명": "인천지하철 1호선"})
    assert r["name"] == "검단호수공원" and r["line"] == "인천지하철 1호선"
    assert normalize_station({"역명": "논현", "경도": "127.0220546", "위도": "37.5096469", "선명": "신분당선"})["lat"] == 37.5096469
    assert normalize_station({"역명": "X", "위도": "", "경도": "1"}) is None


def test_merge_and_nearest():
    s = merge_stations([{"name": "강남", "line": "2호선", "lat": 37.4979, "lng": 127.0276},
                        {"name": "강남", "line": "신분당선", "lat": 37.4966, "lng": 127.0283},
                        {"name": "역삼", "line": "2호선", "lat": 37.5006, "lng": 127.0364}])
    assert len(s) == 2 and s[0]["lines"] == ["2호선", "신분당선"]
    st, d = nearest(37.4990, 127.0300, s)
    assert st["name"] == "강남" and 150 < d < 350
    assert 700 < dist_m(37.4979, 127.0276, 37.5006, 127.0364) < 950   # 강남~역삼 약 0.8km


def test_merge_drops_conflicting_coordinate():
    # 출처 B 는 다른 역(종합운동장)에서 A 와 맞고, 출처 C 는 어디서도 안 맞는다 → 잠실새내는 B 좌표
    rows = [{"name": "잠실새내", "line": "2호선", "lat": 37.51165, "lng": 127.08622, "src": "B"},
            {"name": "잠실새내", "line": "2호선", "lat": 37.52073, "lng": 127.10374, "src": "C"},      # 1.8km 떨어진 틀린 좌표
            {"name": "종합운동장", "line": "2호선", "lat": 37.5110, "lng": 127.0748, "src": "A"},
            {"name": "종합운동장", "line": "2호선", "lat": 37.5111, "lng": 127.0749, "src": "B"},
            {"name": "종합운동장", "line": "2호선", "lat": 37.5200, "lng": 127.0900, "src": "C"},
            {"name": "양평", "line": "5호선", "lat": 37.5258, "lng": 126.8856},
            {"name": "양평", "line": "경의중앙선", "lat": 37.4926, "lng": 127.4917}]        # 다른 역
    s = merge_stations(rows)
    jam = [x for x in s if x["name"] == "잠실새내"]
    assert len(jam) == 1 and abs(jam[0]["lat"] - 37.5117) < 0.001
    assert len([x for x in s if x["name"] == "양평"]) == 2
