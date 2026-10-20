from collector import redev_gg as G
from collector.redev import general_sale, link

REG = {"41281": "경기 고양시 덕양구", "41285": "경기 고양시 일산동구", "41287": "경기 고양시 일산서구", "41290": "경기 과천시",
       "41590": "경기 화성시"}


def test_parse_addr():
    # 2026-10-20 경기데이터드림 파일의 실제 위치 표기들
    assert G.parse_addr("경기도 고양시 덕양구 관산동 178-57번지 일원", "고양시") == ("덕양구", "관산동", 178, 57)
    assert G.parse_addr("경기도 군포시 군포시 당동 768번지 일원", "군포시") == (None, "당동", 768, 0)
    assert G.parse_addr("경기도 안양시 안양시 만안구 안양동43-1", "안양시") == ("만안구", "안양동", 43, 1)
    assert G.parse_addr("경기도 안양시 동안구 호계1동 977", "안양시") == ("동안구", "호계동", 977, 0)
    assert G.parse_addr("경기도 성남시 산성대로 383번길 14(단대동 177)", "성남시") == (None, "단대동", 177, 0)
    assert G.parse_addr("경기도 용인시 처인구 삼가동 110", "용인시") == ("처인구", "삼가동", 110, 0)
    assert G.parse_addr("경기도 파주시 아동동 275-13", "파주시") == (None, "아동동", 275, 13)
    assert G.parse_addr("경기도 남양주시 진접읍 내각리 산31-7일원", "남양주시") == (None, "진접읍 내각리", None, None)
    assert G.parse_addr("경기도 광명시 nan", "광명시") == (None, None, None, None)


def test_zone_row_region_umd():
    r = {"시군명": "과천시", "사업단계": "관리처분", "사업유형": "재건축", "정비구역명": "주공8,9단지구역", "위치": "경기도 과천시 부림동 41번지",
         "(기존주택)세대수": "2,120", "조합원분양세대수": "2058", "일반분양세대수": "709", "(기존)용적률": "130%", "(신축)용적률": "237%",
         "추진위승인일자": "20190415", "조합설립인가일자": "20200828", "관리처분인가일자": "", "(기존주택)준공년도": "1983"}
    z = G.zone_row(r)
    assert (z["code"], z["src"], z["stage"], z["stage_no"], z["existing_hh"], z["gen_hh"], z["sale_hh"]) == \
        ("GG-과천시-주공8,9단지구역", "gg", "관리처분", 6, 2120, 709, 2767)
    assert (z["vl_old"], z["vl_new"], z["committee_ymd"], z["mgmt_ymd"], z["umd_name"], z["bun"]) == (130.0, 237.0, "2019-04-15", None, "부림동", 41)
    assert G.region_code(z, REG, {}) == "41290"
    # 구가 있는 시인데 주소에 구가 없으면 같은 시 단지의 법정동으로
    y = G.zone_row({"시군명": "고양시", "사업단계": "준공", "사업유형": "재건축", "정비구역명": "원당주공2단지", "위치": "경기도 고양시 성사동 715번지"})
    assert y["stage_no"] == 8 and G.region_code(y, REG, {("41281", "성사동"): "41281"}) == "41281"
    # 화성시는 '상신리'처럼 읍 없이 적혀 있다 → 단지 법정동 '향남읍 상신리'
    h = G.zone_row({"시군명": "화성시", "사업단계": "예정구역", "사업유형": "재건축", "정비구역명": "향남01", "위치": "경기도 화성시 상신리 623"})
    assert G.full_umd(h, REG, [{"region_code": "41590", "umd_name": "향남읍 상신리"}]) == "향남읍 상신리"
    assert G.zone_row({"시군명": "x", "사업단계": "청산", "사업유형": "재개발", "정비구역명": "a", "위치": ""})["stage"] == "준공"


def test_link_skips_new_and_done():
    base = {"region_code": "41290", "umd_name": "부림동", "bun": 41, "ji": 0, "biz_type": "재건축", "zone_nm": "주공8,9단지구역"}
    zs = [dict(base, code="z1", stage_no=7, committee_ymd="2019-04-15"),
          dict(base, code="z2", stage_no=8, umd_name="별양동", bun=1)]
    cx = [{"apt_seq": "old", "apt_name": "주공8", "region_code": "41290", "umd_name": "부림동", "jibun": "41", "build_year": 1983},
          {"apt_seq": "new", "apt_name": "과천새단지", "region_code": "41290", "umd_name": "부림동", "jibun": "41", "build_year": 2025},
          {"apt_seq": "done", "apt_name": "x", "region_code": "41290", "umd_name": "별양동", "jibun": "1", "build_year": 1983}]
    assert link(zs, cx) == [("old", "z1", "jibun")]


def test_general_sale_gg_direct_and_by_sido():
    zs = [{"code": "s", "biz_type": "공동주택재건축", "existing_hh": 100, "sale_hh": 300, "region_code": "11680"},
          {"code": "g1", "biz_type": "재건축", "existing_hh": 100, "gen_hh": 50, "sale_hh": 999, "region_code": "41290"},
          {"code": "g2", "biz_type": "재건축", "existing_hh": 100, "gen_hh": 10, "region_code": "41290"},
          {"code": "g3", "biz_type": "재건축", "existing_hh": 100, "gen_hh": 90, "region_code": "41290", "stage_no": 8}]
    g = general_sale(zs)
    assert g["s"] == (200, 2.0, 100.0)                      # 서울은 근사, 서울끼리 순위
    assert g["g1"] == (50, 0.5, 100.0) and g["g2"] == (10, 0.1, 50.0) and "g3" not in g   # 경기는 원자료 값, 준공 제외
