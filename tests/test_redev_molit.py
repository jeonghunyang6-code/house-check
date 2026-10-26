from collector import redev_molit as M

Z = [{"code": "a", "district": "수원시", "zone_nm": "영통 3구역(원천 주공)", "stage_no": 0},
     {"code": "b", "district": "광명시", "zone_nm": "철산주공10,11단지", "stage_no": 3},
     {"code": "c", "district": "용인시", "zone_nm": "기흥1", "stage_no": 1},
     {"code": "d", "district": "구리시", "zone_nm": "수택지구", "stage_no": 1}]


def test_stage_of():
    assert M.stage_of("4)조합설립인가") == ("조합설립", 3) and M.stage_of("17)사업시행자지정") == ("조합설립", 3)
    assert M.stage_of("9)모름") is None


def test_match():
    assert M.match({"시군구": "수원영통구", "구역명칭": "영통3구역(원천주공)"}, Z)["code"] == "a"
    assert M.match({"시군구": "용인기흥구", "구역명칭": "기흥1(구갈한성1차)"}, Z)["code"] == "c"
    # 2026-10-26 시험에서 잘못 붙던 것: 다른 동 같은 번호, 한 글자 다른 짧은 이름
    assert M.match({"시군구": "광명시", "구역명칭": "하안주공10·11단지"}, Z) is None
    assert M.match({"시군구": "구리시", "구역명칭": "수택E"}, Z) is None
