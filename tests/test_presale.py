from collector.presale import address_candidates, month_add, parse_item


def test_parse_item():
    it = {"HOUSE_MANAGE_NO": "2026000399", "HOUSE_NM": " 브라운스톤 월곡 센트럴 ", "HSSPLY_ADRES": "서울특별시 성북구 하월곡동 70-4번지 일원",
          "TOT_SUPLY_HSHLDCO": 62, "MVN_PREARNGE_YM": "202903", "RCRIT_PBLANC_DE": "2026-08-28", "HOUSE_SECD_NM": "APT",
          "SUBSCRPT_AREA_CODE_NM": "서울"}
    p = parse_item(it)
    assert (p["house_no"], p["name"], p["households"], p["move_in_ym"], p["area"]) == ("2026000399", "브라운스톤 월곡 센트럴", 62, "202903", "서울")
    assert parse_item(dict(it, MVN_PREARNGE_YM="")) is None and parse_item(dict(it, MVN_PREARNGE_YM="202913")) is None


def test_address_candidates():
    assert address_candidates("서울특별시 성북구 하월곡동 70-4번지 일원") == [
        ("jibun", "서울특별시 성북구 하월곡동 70-4"), ("dong", "서울특별시 성북구 하월곡동")]
    assert address_candidates("경기도 화성시 동탄면 영천리 일원") == [("dong", "경기도 화성시 동탄면 영천리")]
    assert address_candidates("인천광역시 계양구 귤현동, 동양동, 박촌동 일원 인천계양 A17블록") == [("dong", "인천광역시 계양구 귤현동")]
    assert address_candidates("인천광역시 부평구 산곡동 10번지 일원(산곡6 주택재개발정비사업)")[0] == ("jibun", "인천광역시 부평구 산곡동 10")


def test_month_add():
    assert (month_add("202611", 2), month_add("202601", -1), month_add("202612", 24)) == ("202701", "202512", "202812")
