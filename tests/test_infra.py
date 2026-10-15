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


def test_drop_shared_coords():
    from collector.infra import drop_shared_coords
    rows = [{"src": "a", "name": "별내", "lat": 37.642221, "lng": 127.127208},
            {"src": "a", "name": "사릉", "lat": 37.642221, "lng": 127.127208},
            {"src": "a", "name": "금곡", "lat": 37.637414, "lng": 127.207931},
            {"src": "b", "name": "별내", "lat": 37.64217, "lng": 127.1273},
            {"src": "c", "name": "의정부", "lat": 37.73873, "lng": 127.045891},
            {"src": "c", "name": "청산", "lat": 37.73873, "lng": 127.045891}]
    assert [(r["src"], r["name"]) for r in drop_shared_coords(rows)] == [
        ("a", "별내"), ("a", "금곡"), ("b", "별내"), ("c", "의정부"), ("c", "청산")]
    rows.append({"src": "kakao", "name": "청산", "lat": 37.995089, "lng": 127.074274})   # 다른 출처가 다른 자리 → 공유 좌표 쪽을 뺀다
    assert [(r["src"], r["name"]) for r in drop_shared_coords(rows)][-2:] == [("c", "의정부"), ("kakao", "청산")]


def test_hira_items_and_grid():
    from collector import hira
    body = {"response": {"body": {"totalCount": 2, "items": {"item": [
        {"yadmNm": "서울아산병원", "clCd": "01", "clCdNm": "상급종합", "XPos": "127.1080", "YPos": "37.5268"},
        {"yadmNm": "좌표없음의원", "clCd": "31", "clCdNm": "의원", "XPos": "", "YPos": ""}]}}}}
    total, rows = hira.items(body)
    assert total == 2 and len(rows) == 2
    pts = [p for p in map(hira.normalize, rows) if p]
    assert pts == [{"name": "서울아산병원", "kind": "01", "kind_nm": "상급종합", "lat": 37.5268, "lng": 127.108}]
    one = {"response": {"body": {"totalCount": 1, "items": {"item": {"yadmNm": "a", "XPos": "127", "YPos": "37.5"}}}}}
    assert len(hira.items(one)[1]) == 1
    g = hira.Grid([{"lat": 37.5, "lng": 127.0}, {"lat": 37.5, "lng": 127.009}, {"lat": 37.5, "lng": 127.02}])
    assert hira.count_within(g, 37.5, 127.0, 1000) == 2          # 0m, 약 795m 안 / 1.77km 밖


def test_schoolinfo_match_and_rate():
    from collector import schoolinfo
    gudo = {"B1": {"name": "서울대치중학교", "lat": 37.4950, "lng": 127.0600},
            "B2": {"name": "도곡중학교", "lat": 37.4900, "lng": 127.0500},
            "B3": {"name": "없는중학교", "lat": 37.3000, "lng": 127.0000}}
    info = [{"SCHUL_CODE": "S1", "SCHUL_NM": "대치중학교", "LTTUD": 37.4955, "LGTUD": 127.0602},
            {"SCHUL_CODE": "S2", "SCHUL_NM": "도곡중학교(이전)", "LTTUD": 37.4903, "LGTUD": 127.0501}]
    m = schoolinfo.match(gudo, info)
    assert m["B1"]["SCHUL_CODE"] == "S1"            # 이름(서울 접두 뺌)·300m 안
    assert m["B2"]["SCHUL_CODE"] == "S2"            # 이름은 달라도 100m 안 하나뿐
    assert "B3" not in m
    assert schoolinfo.net_in_rate({"STDNT_SUM": 886, "MVIN_SUM": 41, "MVT_SUM": 59}) == -2.0
    assert schoolinfo.net_in_rate({"STDNT_SUM": 0, "MVIN_SUM": 1, "MVT_SUM": 0}) is None


def test_drop_strays():
    from collector.infra import drop_strays
    st = lambda name, lines, lat, lng, w=1.0: {"name": name, "lines": lines, "lat": lat, "lng": lng, "n": 1, "w": w}
    rows = [st("수서", ["3호선"], 37.4872, 127.1017, 2), st("대모산입구", ["수인분당"], 37.4914, 127.0727), st("일원", ["3호선"], 37.4836, 127.0846),
            st("수서", ["수인분당"], 37.2915, 127.676),                        # 이천에 찍힌 틀린 좌표
            st("양평", ["5호선"], 37.5256, 126.8862, 2), st("영등포구청", ["5호선"], 37.5246, 126.8960),
            st("양평", ["경의중앙"], 37.4927, 127.4919), st("오빈", ["경의중앙"], 37.5061, 127.4734),
            st("용답", ["2호선"], 37.5621, 127.0509, 2), st("용답", ["2호선"], 37.5664, 126.9779)]
    out = drop_strays(rows)
    names = [(s["name"], tuple(s["lines"])) for s in out]
    assert ("수서", ("3호선", "수인분당")) in names and len([n for n in names if n[0] == "수서"]) == 1
    assert len([n for n in names if n[0] == "양평"]) == 2
    assert len([n for n in names if n[0] == "용답"]) == 1
