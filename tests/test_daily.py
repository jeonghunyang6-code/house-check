from datetime import date

from collector.regions import REGIONS, select_regions
from jobs.daily import default_months, parse_months


def test_default_months_kst_current_and_previous():
    assert default_months(date(2026, 10, 11)) == ["202610", "202609"]
    assert default_months(date(2027, 1, 1)) == ["202701", "202612"]


def test_parse_months_ranges_and_lists():
    assert parse_months("202611-202702") == ["202611", "202612", "202701", "202702"]
    assert parse_months("202608,202609") == ["202608", "202609"]
    assert len(parse_months("202001-202512")) == 72


def test_regions_are_verified_codes():
    assert all(len(c) == 5 and c.isdigit() for c in REGIONS)
    assert len(select_regions("seoul")) == 25 and all(c.startswith("11") for c in select_regions("seoul"))
    assert set(select_regions("sudogwon")) == set(REGIONS)
    # 2026-07 인천 개편: 옛 코드(중구 28110, 동구 28140, 서구 28260)는 API 가 0건을 돌려준다
    assert not {"28110", "28140", "28260"} & set(REGIONS)
    assert select_regions("11680,41597") == ["11680", "41597"]
