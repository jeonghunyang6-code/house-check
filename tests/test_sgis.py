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


def test_rural_ri_and_junk_jibun():
    # 2026-10-27: 화성 만세·효행구 읍면 리 단지가 SGIS 의 '남양리'(끝 이름만)와 안 맞아 138곳 좌표 없음
    hit = {"leg_cd": "4159025021", "leg_nm": "남양리", "sgg_nm": "화성시"}
    assert accept(hit, "4159125021", "남양읍 남양리", "경기 화성시 만세구")
    assert not accept({"leg_nm": "남양리", "sgg_nm": "평택시"}, None, "남양읍 남양리", "경기 화성시 만세구")
    # 지번 받기 전 블록 값은 지번 후보로 쓰지 않는다(SGIS 서버 오류)
    assert all(m != "jibun" for m, _ in address_candidates("경기 화성시 효행구", "봉담읍 동화리", "지구BL", None, None))
    assert address_candidates("경기 화성시 효행구", "봉담읍 동화리", "산12-3", None, None)[0][0] == "jibun"
