from collector.adjacency import adjacency, area_centroid, side_of


def sq(x, y, s=1000):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + s / 2, y], [x + s, y], [x + s, y + s / 2], [x + s, y + s],
                                                [x + s / 2, y + s], [x, y + s], [x, y + s / 2], [x, y]]]}


def test_area_centroid():
    a, cx, cy = area_centroid(sq(0, 0))
    assert round(a) == 1_000_000 and round(cx) == 500 and round(cy) == 500


def test_adjacency_and_river():
    f = [{"adm_cd": "A", "adm_nm": "서울특별시 성동구 성수1가1동", "geometry": sq(0, 0)},
         {"adm_cd": "B", "adm_nm": "서울특별시 강남구 압구정동", "geometry": sq(0, 1000)},     # 위로 맞닿음 (강 건너)
         {"adm_cd": "C", "adm_nm": "서울특별시 성동구 성수2가1동", "geometry": sq(1000, 0)},   # 옆으로 맞닿음
         {"adm_cd": "D", "adm_nm": "서울특별시 성동구 금호동", "geometry": sq(5000, 5000)}]    # 떨어짐
    got = {(a, b): river for a, b, n, river in adjacency(f)}
    assert got == {("A", "B"): True, ("A", "C"): False}         # A-C 대각선 닿은 B-C 는 꼭짓점 1개라 제외


def test_side_of():
    assert side_of("서울특별시 송파구 풍납1동") == "S"
    assert side_of("경기도 고양시 덕양구 화정1동") == "N"
    assert side_of("경기도 양평군 양평읍") is None
