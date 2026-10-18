import json
from datetime import date
from pathlib import Path

import pytest

from collector.regions import REGIONS
from collector.sources.molit import ApiError
from collector.sources.rone import keep, map_regions, parse, week_id, weeks_between

FX = Path(__file__).parent / "fixtures"
# 2026-10-12 실제 응답(매매가격지수 202641 주)에서 6개 지역만 뽑은 것
SALE = json.loads((FX / "rone_sale_202641.json").read_text(encoding="utf-8"))
SUPPLY = json.loads((FX / "rone_supply_sample.json").read_text(encoding="utf-8"))


def wrap(rows):
    return {"SttsApiTblData": [{"head": [{"list_total_count": len(rows)}, {"RESULT": {"CODE": "INFO-000"}}]}, {"row": rows}]}


def test_parse_and_keep():
    pts = parse(wrap(SALE))
    assert len(pts) == 6 and all(p.week_id == "202641" and p.week_date == date(2026, 10, 5) for p in pts)
    names = {p.full_name for p in pts if keep("sale", p)}
    assert "충남>천안시>동남구" not in names and {"서울", "수도권", "인천>제물포구"} <= names
    assert all(keep("sale_supply", p) for p in parse(wrap(SUPPLY)))


def test_no_data_and_error():
    assert parse({"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}) == []
    with pytest.raises(ApiError):
        parse({"RESULT": {"CODE": "ERROR-290", "MESSAGE": "인증키가 유효하지 않습니다."}})


def test_iso_week_ids_match_rone():
    assert week_id(date(2026, 10, 5)) == "202641" and week_id(date(2025, 9, 29)) == "202540"
    assert weeks_between(date(2026, 9, 24), date(2026, 10, 8)) == ["202639", "202640", "202641"]
    assert weeks_between(date(2026, 12, 28), date(2027, 1, 5)) == ["202653", "202701"]


def test_region_mapping():
    full = ["서울>강남지역>동남권>강남구", "경기>경부2권>수원시>영통구", "인천>제물포구", "경기>동부1권>하남시", "경기>경부2권>수원시"]
    m = map_regions(full, REGIONS)
    assert m["서울>강남지역>동남권>강남구"] == "11680" and m["경기>경부2권>수원시>영통구"] == "41117"
    assert m["인천>제물포구"] == "28125" and m["경기>동부1권>하남시"] == "41450"
    assert "경기>경부2권>수원시" not in m  # 시 집계는 시군구 코드에 연결하지 않는다 (일반구가 따로 있음)


def test_parse_buyer_and_codes():
    from collector.regions import REGIONS
    from collector.sources.rone import buyer_codes, parse_buyer
    rows = [{"GRP_ID": "910098", "GRP_FULLNM": "서울>송파구", "CLS_NM": c, "ITM_ID": "100001", "DTA_VAL": v, "WRTTIME_IDTFR_ID": "202608"}
            for c, v in (("합계", 266), ("관할시군구내", 116), ("관할시도내", 92), ("관할시도외_서울", 0), ("관할시도외_기타", 58))]
    rows += [{"GRP_ID": "910098", "GRP_FULLNM": "서울>송파구", "CLS_NM": "합계", "ITM_ID": "100002", "DTA_VAL": 22.5, "WRTTIME_IDTFR_ID": "202608"},
             {"GRP_ID": "900001", "GRP_FULLNM": None, "GRP_NM": "전국", "CLS_NM": "합계", "ITM_ID": "100001", "DTA_VAL": 1, "WRTTIME_IDTFR_ID": "202608"},
             {"GRP_ID": "910200", "GRP_FULLNM": "부산>중구", "CLS_NM": "합계", "ITM_ID": "100001", "DTA_VAL": 5, "WRTTIME_IDTFR_ID": "202608"}]
    out = parse_buyer(rows)
    assert out == [{"period": "202608", "grp_id": 910098, "name": "서울>송파구", "total": 266, "same_sgg": 116, "same_sido": 92, "seoul": 0, "other": 58}]
    assert buyer_codes("서울>송파구", REGIONS) == ["11710"]
    assert buyer_codes("경기>수원시", REGIONS) == ["41111", "41113", "41115", "41117"]
    assert buyer_codes("서울", REGIONS) == [] and buyer_codes("인천>(구)중구", REGIONS) == []
