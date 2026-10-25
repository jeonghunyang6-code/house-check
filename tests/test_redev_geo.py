from jobs import redev_geo as G


def test_query_of_builds_full_address():
    z = {"region_code": "11170", "umd_name": "동자동", "bun": 15, "ji": 1, "jibun_addr": "동자동15-1"}
    assert G.query_of(z).startswith("서울특별시 ") and G.query_of(z).endswith("동자동 15-1")


def test_query_of_falls_back_to_address_text():
    # 시군구를 못 정한 경기 구역(2026-10-25 이 행에서 멈췄음), 번지 없는 '산…일원'
    assert G.query_of({"region_code": None, "umd_name": "계수동", "bun": 1, "ji": 6, "jibun_addr": "경기도 부천시 계수동 1-6"}) == "경기도 부천시 계수동 1-6"
    assert G.query_of({"region_code": "41360", "umd_name": "금곡동", "bun": None, "ji": None,
                       "jibun_addr": "경기도 남양주시 금곡동 산108-1일원"}) == "경기도 남양주시 금곡동 산108-1"
