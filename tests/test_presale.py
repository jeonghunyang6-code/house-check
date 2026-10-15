from collector.infra import dist_m
from collections import Counter

from collector.presale import (address_candidates, locate, match_complex, month_add, name_overlap, parse_item, parse_plan,
                               total_households)


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


def test_match_and_total():
    assert name_overlap("올림픽파크 포레온", "올림픽파크포레온") == 8 and name_overlap("브라운스톤 월곡", "래미안월곡") == 2
    p = {"name": "래미안 원베일리", "move_in_ym": "202308", "lat": 37.5070, "lng": 127.0000}
    cands = [{"name": "래미안원베일리", "lat": 37.5072, "lng": 127.0003, "build_year": 2023, "households": 2990},
             {"name": "래미안원베일리", "lat": 37.5200, "lng": 127.0000, "build_year": 2023, "households": 1},     # 1.4km
             {"name": "반포자이", "lat": 37.5071, "lng": 127.0001, "build_year": 2023, "households": 3410}]          # 이름 다름
    assert match_complex(p, cands, dist_m)["households"] == 2990
    assert match_complex(dict(p, move_in_ym="202008"), cands, dist_m) is None                                       # 준공 연도 차이
    rows = [{"house_no": f"h{i}", "name": f"단지{i}", "households": 100, "imprmn": True} for i in range(6)] + [
        {"house_no": "new", "name": "새단지", "households": 200, "imprmn": True}, {"house_no": "plain", "name": "일반", "households": 300, "imprmn": False},
        {"house_no": "h0b", "name": "단지0(조합원 취소분)", "households": 1, "imprmn": True},
        {"house_no": "h1b", "name": "단지1 2차", "households": 40, "imprmn": True}]
    matched = {f"h{i}": (250 + 10 * i, f"s{i}") for i in range(6)} | {"h0b": (250, "s0"), "h1b": (260, "s1")}
    ratio, tot = total_households(rows, matched)
    assert ratio == 2.75 and tot["new"] == (550, "추정 ×2.75") and tot["plain"] == (300, "공급") and tot["h0"] == (250, "K-apt")
    assert tot["h0b"] == (0, "중복") and tot["h1b"] == (0, "중복")      # 취소분 이름, 같은 단지 두 번째 공고


def test_parse_plan_and_locate():
    text = ("입주예정월,지역,사업유형,주소,아파트명,세대수\n2027-12,서울,분양임대,서울특별시 서초구 반포동 810-0,반포디에이치클래스트,5007\n"
            "2026-12,강원,분양,강원특별자치도 강릉시 견소동 219-0,강릉,561\n2027-01,경기,분양,경기도 화성특례시 동탄구 영천동 1-1,동탄,900\n")
    rows = parse_plan(text)
    assert [(r["name"], r["move_in_ym"], r["households"], r["kind"]) for r in rows] == [
        ("반포디에이치클래스트", "202712", 5007, "분양임대"), ("동탄", "202701", 900, "분양")]
    idx = {("서울", "반포동"): Counter({("11650", "Z9"): 5, ("11650", "Z8"): 2}), ("경기", "영천동"): Counter({("41597", "Z3"): 1})}
    regions = {"11650": "서울 서초구", "41597": "경기 화성시 동탄구"}
    assert locate(rows[0]["address"], idx, regions) == ("11650", "Z9")
    assert locate(rows[1]["address"], idx, regions) == ("41597", "Z3")        # 특례시 → 시
    assert locate("서울특별시 강남구 반포동 1", idx, regions) == (None, None)   # 시군구가 다르면 아님
