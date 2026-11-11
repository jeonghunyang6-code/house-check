from collector.parks import items, keep, normalize


def test_items_shapes():
    body = {"response": {"header": {"resultCode": "00"}, "body": {"items": [{"parkNm": "a"}], "totalCount": "12"}}}
    assert items(body) == (12, [{"parkNm": "a"}])
    one = {"response": {"body": {"items": {"item": {"parkNm": "b"}}, "totalCount": 1}}}
    assert items(one) == (1, [{"parkNm": "b"}])
    assert items({"response": {"body": {"items": "", "totalCount": "0"}}}) == (0, [])


def test_normalize_and_keep():
    r = {"parkNm": " 고덕근린공원 ", "parkSe": "근린공원", "latitude": "37.556", "longitude": "127.161", "parkAr": "21,000",
         "rdnmadr": "서울특별시 강동구 고덕동"}
    p = normalize(r)
    assert p["name"] == "고덕근린공원" and p["area"] == 21000 and keep(p)
    assert not keep(normalize({**r, "parkSe": "어린이공원"})) and not keep(normalize({**r, "parkSe": "소공원"}))
    assert not keep(normalize({**r, "rdnmadr": "부산광역시 해운대구"}))
    assert keep(normalize({**r, "rdnmadr": "", "lnmadr": ""}))                 # 주소 없으면 좌표로 수도권
    assert normalize({**r, "latitude": ""}) is None and normalize({**r, "latitude": "0"}) is None
