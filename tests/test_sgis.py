from collector.sgis import accept, address_candidates


def test_address_candidates():
    c = address_candidates("서울 송파구", "가락동", "913", "송파대로 345", None)
    assert c == [("jibun", "서울특별시 송파구 가락동 913"), ("road", "서울특별시 송파구 송파대로 345")]
    c = address_candidates("경기 화성시 동탄구", "장지동", "976", None, "경기도 화성시 동탄대로4가길 26")
    assert c == [("jibun", "경기도 화성시 동탄구 장지동 976"), ("jibun", "경기도 화성시 장지동 976"),
                 ("kapt_road", "경기도 화성시 동탄대로4가길 26")]


def test_accept():
    hit = {"leg_cd": "1171010700", "leg_nm": "가락동", "sgg_nm": "송파구", "x": "127.1", "y": "37.5"}
    assert accept(hit, "1171010700", "가락동", "서울 송파구")
    assert accept(hit, "9999999999", "가락동", "서울 송파구")      # 시군구 개편으로 코드가 달라도 이름이 같으면
    assert not accept(hit, "1171010800", "문정동", "서울 송파구")
    assert not accept({**hit, "leg_nm": "신정동", "sgg_nm": "마포구"}, "1147010100", "신정동", "서울 양천구")
    assert accept({**hit, "leg_nm": "장지동", "sgg_nm": "화성시"}, "4159711100", "장지동", "경기 화성시 동탄구")
    assert not accept(None, "1171010700", "가락동")
