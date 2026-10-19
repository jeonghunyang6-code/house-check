from collector.redev import general_sale, link, parse_addr, zone_row


def test_parse_addr():
    # 2026-10-19 실제 응답 표기
    assert parse_addr("양천구목동903") == ("목동", 903, 0)
    assert parse_addr("쌍문2동 81번지") == ("쌍문동", 81, 0)
    assert parse_addr("효창동 5-307") == ("효창동", 5, 307)
    assert parse_addr("이문동170-65") == ("이문동", 170, 65)
    assert parse_addr("성수동1가 656") == ("성수동1가", 656, 0)
    assert parse_addr("압구정동414") == ("압구정동", 414, 0)        # '압구'를 구 이름으로 떼지 않는다
    assert parse_addr("") is None and parse_addr("-") is None


def test_zone_row_and_link():
    regions = {"11470": "서울 양천구", "11350": "서울 노원구"}
    z = zone_row({"CODE": "2813", "DISTRICT": "양천구", "ZONE_NM": "목동2단지", "JIBUN_ADDR": "양천구목동902", "BIZ_TYPE": "공동주택재건축",
                  "BIZ_STAGE": "조합설립", "EXISTING_HOUSEHOLDS": "1640", "TOT_BUILT_HOUSEHOLDS": "3389", "ASSOCIATION_ESTABLISHMENT_YMD": "2026-02-19",
                  "MIGRATION_END_YMD": "-"}, regions)
    assert (z["region_code"], z["umd_name"], z["bun"], z["stage_no"], z["existing_hh"], z["assoc_ymd"]) == ("11470", "목동", 902, 3, 1640, "2026-02-19")
    z2 = zone_row({"CODE": "2896", "DISTRICT": "노원구", "ZONE_NM": "태릉우성아파트", "JIBUN_ADDR": "공릉동 999", "BIZ_TYPE": "공동주택재건축",
                   "BIZ_STAGE": "구역지정"}, regions)
    z3 = zone_row({"CODE": "1", "DISTRICT": "노원구", "ZONE_NM": "상계1구역", "JIBUN_ADDR": "상계동 1", "BIZ_TYPE": "주택정비형 재개발",
                   "BIZ_STAGE": "착공"}, regions)
    cx = [{"apt_seq": "A", "apt_name": "목동신시가지2", "region_code": "11470", "umd_name": "목동", "jibun": "902"},
          {"apt_seq": "B", "apt_name": "목동신시가지3", "region_code": "11470", "umd_name": "목동", "jibun": "903"},
          {"apt_seq": "C", "apt_name": "태릉우성", "region_code": "11350", "umd_name": "공릉동", "jibun": "254"},
          {"apt_seq": "D", "apt_name": "상계주공1", "region_code": "11350", "umd_name": "상계동", "jibun": "1"}]
    assert link([z, z2, z3], cx) == [("A", "2813", "jibun"), ("C", "2896", "name")]   # 재개발 구역은 단지와 잇지 않는다
    # 이촌동 300-xx 처럼 본번이 같은 단지가 여럿: 지번 전체가 같은 곳만, 이름이 동 이름뿐이면 잇지 않는다
    regions["11170"] = "서울 용산구"
    w = zone_row({"CODE": "9", "DISTRICT": "용산구", "ZONE_NM": "왕궁아파트", "JIBUN_ADDR": "이촌동 300-1", "BIZ_TYPE": "공동주택재건축", "BIZ_STAGE": "조합설립"}, regions)
    y = zone_row({"CODE": "8", "DISTRICT": "용산구", "ZONE_NM": "이촌동(1,2,3)", "JIBUN_ADDR": "이촌동 999", "BIZ_TYPE": "공동주택재건축", "BIZ_STAGE": "추진위"}, regions)
    ix = [{"apt_seq": "W", "apt_name": "왕궁", "region_code": "11170", "umd_name": "이촌동", "jibun": "300-1"},
          {"apt_seq": "H", "apt_name": "한강맨숀", "region_code": "11170", "umd_name": "이촌동", "jibun": "300-23"},
          {"apt_seq": "E", "apt_name": "이촌동그린빌", "region_code": "11170", "umd_name": "이촌동", "jibun": "12"}]
    assert link([w, y], ix) == [("W", "9", "jibun")]


def test_general_sale():
    # 2026-10-19 실제 값: 대치쌍용2차 기존 364 → 분양 1,165 (일반분양 근사 801, 2.2배), 신반포16차 396 → 400
    zs = [{"code": "a", "biz_type": "공동주택재건축", "existing_hh": 364, "sale_hh": 1165},
          {"code": "b", "biz_type": "공동주택재건축", "existing_hh": 396, "sale_hh": 400},
          {"code": "c", "biz_type": "아파트지구재건축", "existing_hh": 213, "sale_hh": 185},
          {"code": "d", "biz_type": "공동주택재건축", "existing_hh": 0, "sale_hh": 500},
          {"code": "e", "biz_type": "주택정비형 재개발", "existing_hh": 100, "sale_hh": 900}]
    g = general_sale(zs)
    assert set(g) == {"a", "b", "c"}
    assert g["a"] == (801, 2.2, 100.0) and g["b"][0] == 4 and g["c"] == (-28, -0.13, 33.3)
