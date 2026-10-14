from collector.neis import count_by_dong, match_dong, parse_place


def test_parse_place():
    assert parse_place("서울특별시 강남구 개포로82길 7", ", 3층 301호 (개포동, 삼성빌딩)") == ("서울", "강남구", "개포동")
    assert parse_place("경기도 수원시 영통구 봉영로 1612", ", 4층 (영통동)") == ("경기", "수원시 영통구", "영통동")
    assert parse_place("경기도 광주시 초월읍 경충대로 1", ", 2층") == ("경기", "광주시", "초월읍")
    assert parse_place("서울특별시 종로구 종로 1", " (종로1가)") == ("서울", "종로구", "종로1가")
    assert parse_place("서울특별시 강남구 삼성로 150", ", 158호") is None
    assert parse_place("부산광역시 해운대구 x로 1", " (우동)") is None


def test_count_and_match():
    def row(state, realm, kind, road, det):
        return {"REG_STTUS_NM": state, "REALM_SC_NM": realm, "ACA_INSTI_SC_NM": kind, "FA_RDNMA": road, "FA_RDNDA": det}
    rows = [row("개원", "입시.검정 및 보습", "학원", "서울특별시 강남구 삼성로 1", " (대치동)"),
            row("개원", "입시.검정 및 보습", "교습소", "서울특별시 강남구 삼성로 2", " (대치동)"),
            row("개원", "예능(대)", "학원", "서울특별시 강남구 삼성로 3", " (대치동)"),
            row("폐원", "입시.검정 및 보습", "학원", "서울특별시 강남구 삼성로 4", " (대치동)"),
            row("개원", "입시.검정 및 보습", "학원", "인천광역시 서구 x로 1", " (청라동)"),
            row("개원", "입시.검정 및 보습", "학원", "경기도 화성시 x로 1", " (영천동)"),
            row("개원", "입시.검정 및 보습", "학원", "서울특별시 x", "")]
    c, miss = count_by_dong(rows)
    assert c[("서울", "강남구", "대치동")] == {"n": 3, "exam": 2, "exam_hagwon": 1}
    assert miss == 1
    assert match_dong(c, "서울", "강남구", "대치동") == ("서울", "강남구", "대치동")
    assert match_dong(c, "인천", "서해구", "청라동") == ("인천", "서구", "청라동")        # 개편 전 이름
    assert match_dong(c, "경기", "화성시 동탄구", "영천동") == ("경기", "화성시", "영천동")
    assert match_dong(c, "경기", "광주시", "초월읍 대쌍령리") is None
    c[("서울", "송파구", "잠실동")] = {"n": 1, "exam": 1, "exam_hagwon": 1}
    assert match_dong(c, "서울", "송파구", "대치동") is None                                # 송파구는 주소에 있으니 ③ 안 씀
