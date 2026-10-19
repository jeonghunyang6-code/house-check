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
    assert info_row({"kaptdaCnt": 0.0, "hoCnt": 2529})["households"] == 2529     # 세대수 0 → 호수


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


def test_match_narrows_same_jibun():
    # 2026-10-19 실제 DB에서 미연결이던 사례 (같은 지번에 K-apt 단지 여럿)
    def k(code, name, sale="분양"):
        return {"kapt_code": code, "kapt_name": name, "bjd_code": "1", "addr": f"서울 중구 신당동 844 {name}", "road_addr": None, "sale_type": sale}
    kapts = [k("N1", "신당남산타운임대", "임대"), k("N2", "신당남산타운(분양)")]
    cx = [{"apt_seq": "s", "apt_name": "남산타운", "bjd_code": "1", "jibun": "844", "road_addr": ""}]
    assert match_complexes(cx, kapts)["s"].kapt_code == "N2"                      # 임대 동 빼기
    kapts = [k("P1", "중동포도마을삼보"), k("P2", "중동포도마을영남")]
    cx = [{"apt_seq": "s", "apt_name": "포도마을(영남)", "bjd_code": "1", "jibun": "844", "road_addr": ""}]
    assert match_complexes(cx, kapts)["s"].kapt_code == "P2"                      # 건설사 이름 조각
    kapts = [k("D2", "덕유마을주공2단지"), k("D4", "중동덕유마을주공4단지"), k("D1", "중동덕유1(공단)", "임대")]
    cx = [{"apt_seq": "s", "apt_name": "덕유마을(주공4)", "bjd_code": "1", "jibun": "844", "road_addr": ""}]
    assert match_complexes(cx, kapts)["s"].kapt_code == "D4"                      # 차수·단지 번호
    kapts = [k("T1", "산본주공퇴계1차아파트"), k("T2", "금정퇴계2차")]
    cx = [{"apt_seq": "s", "apt_name": "퇴계주공(360~368동)", "bjd_code": "1", "jibun": "844", "road_addr": ""}]
    assert "s" not in match_complexes(cx, kapts)                                  # 가릴 근거 없음 → 미연결
    kapts = [k("S1", "연수시영1차(분양)"), k("S2", "연수승기마을"), k("S3", "연수1차시영임", "임대")]
    cx = [{"apt_seq": "s", "apt_name": "승기마을,연수1차시영", "bjd_code": "1", "jibun": "844", "road_addr": ""}]
    assert "s" not in match_complexes(cx, kapts)                                  # 묶은 이름은 하나만 고르지 않음


def test_get_json_unexpected_body_is_api_error():
    import io, urllib.request
    import pytest
    from collector import kapt
    from collector.sources.molit import ApiError, QuotaExceeded

    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    orig = urllib.request.urlopen
    try:
        urllib.request.urlopen = lambda *a, **k: R(b'{"OpenAPI_ServiceResponse": {"x": 1}}')
        with pytest.raises(ApiError):
            kapt._get_json("https://example.invalid", {})
        urllib.request.urlopen = lambda *a, **k: R(b'{"msg": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"}')
        with pytest.raises(QuotaExceeded):
            kapt._get_json("https://example.invalid", {})
    finally:
        urllib.request.urlopen = orig


class _FakeDb:
    def __init__(self, codes):
        self.codes, self.sql = codes, []

    def query(self, sql):
        self.sql.append(sql)
        if sql.lstrip().startswith("SELECT k.kapt_code"):
            return [{"kapt_code": c} for c in self.codes]
        if "count(*)" in sql:
            return [{"n": 0}]
        return []


def _run_info(monkeypatch, codes, fail_until):
    """fail_until 번째 호출까지는 ApiError, 그 뒤로는 정상."""
    import jobs.kapt as jk
    from collector.sources.molit import ApiError
    calls, slept = [], []

    def fake(code):
        calls.append(code)
        if len(calls) <= fail_until:
            raise ApiError("unexpected body: HTTP_ERROR")
        return {"kaptCode": code, "kaptdaCnt": 100}

    monkeypatch.setattr(jk, "fetch_info", fake)
    monkeypatch.setattr(jk, "select", lambda db, sql: db.query(sql))
    db = _FakeDb(codes)
    rc = jk.run_info(db, 100, date(2026, 10, 13), sleep=slept.append)
    saved = [c for c in codes if any(f"kapt_code = '{c}'" in s for s in db.sql)]
    return rc, calls, slept, saved


def test_run_info_pauses_and_retries_after_fail_streak(monkeypatch):
    import jobs.kapt as jk
    codes = [f"A{i:03d}" for i in range(30)]
    rc, calls, slept, saved = _run_info(monkeypatch, codes, jk.FAIL_STREAK)
    assert slept == [jk.PAUSES[0]]
    assert calls[jk.FAIL_STREAK] == codes[0]      # 쉬고 나서 처음 실패한 단지부터 다시
    assert saved == codes and rc == 1             # 다 받았지만 중간 실패가 있었다


def test_run_info_stops_when_failures_persist(monkeypatch):
    import jobs.kapt as jk
    codes = [f"A{i:03d}" for i in range(200)]
    rc, calls, slept, saved = _run_info(monkeypatch, codes, 10**6)
    assert rc == 2 and slept == list(jk.PAUSES) and saved == []
    assert len(calls) == jk.FAIL_STREAK * (len(jk.PAUSES) + 1)


def test_detail_row_and_walk():
    from collector.kapt import detail_row, station_area, walk_minutes
    r = detail_row({"subwayLine": "3호선, 8호선, 9호선", "subwayStation": "송파역", "kaptdWtimesub": "5분이내", "kaptdWtimebus": "5분이내",
                    "kaptdPcnt": "0", "kaptdPcntu": "12096", "groundElChargerCnt": 0, "undergroundElChargerCnt": 256,
                    "kaptdCccnt": "2685", "welfareFacility": "관리사무소,  노인정"})
    assert r["subway_station"] == "송파역" and r["parking_under"] == 12096 and r["ev_charger"] == 256 and r["welfare"] == "관리사무소, 노인정"
    assert detail_row({"subwayStation": " ", "kaptdWtimesub": ""})["subway_station"] is None
    assert detail_row({})["ev_charger"] is None
    assert [walk_minutes(s) for s in ("5분이내", "5~10분이내", "10~15분이내", "20분초과", "", None, "해당없음")] == [5, 10, 15, 99, None, None, None]
    assert [station_area(s) for s in ("5~10분이내", "10~15분이내", None)] == [True, False, None]
