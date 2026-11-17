from collector import hanbank as H

_GEOM = [{"lat": 37.53, "lon": 127.0 + i * 0.0005} for i in range(101)]   # 동서로 놓인 물가(짧은 선분 100개)
SEGS = H.segments({"elements": [{"type": "way", "geometry": _GEOM}]})
m = lambda d: 37.53 + d / 110940            # 물가에서 북쪽으로 d m
east = lambda x: 127.02 + x / H.KX         # 127.02 에서 동쪽으로 x m
CX = [{"apt_seq": "A", "apt_name": "A", "lat": m(250), "lng": 127.02}, {"apt_seq": "S", "apt_name": "S", "lat": m(120), "lng": 127.0203}]


def test_center_judge():
    got = H.judge(CX, SEGS)
    assert got["S"] == (120, True, None) and got["A"][1] is False and got["A"][2] == "S"


def test_building_judge_sees_side_building():
    behind, side, s_bld = H.xy(m(220), 127.0203), H.xy(m(230), east(150)), H.xy(m(120), 127.0203)
    assert H.judge_buildings(CX, SEGS, [behind, side, s_bld])["A"] == (220, True, None)    # 옆 동은 앞이 트임
    assert H.judge_buildings(CX, SEGS, [behind, s_bld])["A"] == (220, False, "S")          # S 뒤 동만 있으면 가림
