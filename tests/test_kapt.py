from datetime import date

from collector.kapt import info_row, jibun_from_addr, match_complexes, norm_jibun, norm_name, road_from_addr


def test_norm_jibun():
    assert norm_jibun("0316") == "316" and norm_jibun("316-0") == "316" and norm_jibun("12-03") == "12-3"
    assert norm_jibun("189번지") == "189" and norm_jibun("산 12") == "산12" and norm_jibun("") == ""


def test_addr_parsing():
    # 2026-10-12 기본 정보 V5 실제 응답 (개포자이프레지던스)
    assert jibun_from_addr("서울특별시 강남구 개포동 189 개포자이프레지던스") == "189"
    assert jibun_from_addr("경기도 수원시 영통구 매탄동 1272-3 매탄위브하늘채") == "1272-3"
    assert jibun_from_addr("서울특별시 종로구 사직동") == ""
    assert road_from_addr("서울특별시 강남구 삼성로 14") == "삼성로 14"
    assert road_from_addr("서울특별시 강남구 언주로30길 57") == "언주로30길 57"
    assert norm_name("개포자이 프레지던스(1단지)") == "개포자이프레지던스" and norm_name("은마아파트") == "은마"


def test_info_row():
    r = info_row({"kaptAddr": "서울특별시 강남구 개포동 189 개포자이프레지던스", "doroJuso": "서울특별시 강남구 삼성로 14",
                  "kaptdaCnt": 3375.0, "kaptUsedate": "20230228", "kaptDongCnt": "35", "kaptTopFloor": 35,
                  "codeHeatNm": "지역난방", "kaptMparea85": 1848.0})
    assert r["households"] == 3375 and r["use_date"] == date(2023, 2, 28) and r["dong_cnt"] == 35 and r["hh_60_85"] == 1848
    assert info_row({"kaptUsedate": "00000000"})["use_date"] is None


def test_match_priority_and_ambiguity():
    kapts = [
        {"kapt_code": "A1", "kapt_name": "은마아파트", "bjd_code": "1168010600", "addr": "서울특별시 강남구 대치동 316 은마아파트", "road_addr": "서울특별시 강남구 삼성로 212"},
        {"kapt_code": "A2", "kapt_name": "래미안1단지", "bjd_code": "1168010300", "addr": "서울특별시 강남구 개포동 12 래미안1단지", "road_addr": None},
        {"kapt_code": "A3", "kapt_name": "래미안2단지", "bjd_code": "1168010300", "addr": "서울특별시 강남구 개포동 12 래미안2단지", "road_addr": None},
        {"kapt_code": "A4", "kapt_name": "도곡렉슬", "bjd_code": "1168011800", "addr": None, "road_addr": "서울특별시 강남구 선릉로 221"},
        {"kapt_code": "A5", "kapt_name": "타워팰리스", "bjd_code": "1168011800", "addr": None, "road_addr": None},
    ]
    cx = [
        {"apt_seq": "s1", "apt_name": "은마", "bjd_code": "1168010600", "jibun": "0316", "road_addr": ""},           # 지번
        {"apt_seq": "s2", "apt_name": "래미안2단지", "bjd_code": "1168010300", "jibun": "12", "road_addr": ""},      # 지번 2곳 → 이름으로
        {"apt_seq": "s3", "apt_name": "개포주공", "bjd_code": "1168010300", "jibun": "12", "road_addr": ""},         # 지번 2곳, 이름 불일치 → 미연결
        {"apt_seq": "s4", "apt_name": "도곡렉슬", "bjd_code": "1168011800", "jibun": "999", "road_addr": "선릉로 221"},  # 도로명
        {"apt_seq": "s5", "apt_name": "타워팰리스1", "bjd_code": "1168011800", "jibun": "467", "road_addr": ""},     # 이름 포함
    ]
    m = match_complexes(cx, kapts)
    assert {k: (v.kapt_code, v.method) for k, v in m.items()} == {
        "s1": ("A1", "jibun"), "s2": ("A3", "jibun"), "s4": ("A4", "road"), "s5": ("A5", "name")}
