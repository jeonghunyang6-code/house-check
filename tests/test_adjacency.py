from collector.adjacency import adjacency, area_centroid, side_of


def sq(x, y, s=1000, step=100):
    """변마다 step(m) 간격 꼭짓점이 있는 정사각형 (실제 경계처럼 꼭짓점이 촘촘)."""
    n = int(s // step)
    pts = ([[x + i * step, y] for i in range(n)] + [[x + s, y + i * step] for i in range(n)]
           + [[x + s - i * step, y + s] for i in range(n)] + [[x, y + s - i * step] for i in range(n)])
    return {"type": "Polygon", "coordinates": [pts + [pts[0]]]}


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


def test_adjacency_tolerates_small_offsets():
    """맞닿은 변의 꼭짓점이 몇 m 어긋나도 인접 (성내3동 사례)."""
    a = sq(0, 0)
    b = {"type": "Polygon", "coordinates": [[[1008, 3], [2000, 0], [2000, 1000], [1006, 1004]] + [[1000 + (i % 3) * 4, 1000 - i * 100 + 7] for i in range(1, 10)] + [[1008, 3]]]}
    got = adjacency([{"adm_cd": "A", "adm_nm": "", "geometry": a}, {"adm_cd": "B", "adm_nm": "", "geometry": b}])
    assert [(x, y) for x, y, *_ in got] == [("A", "B")]
