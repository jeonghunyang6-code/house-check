import json
from pathlib import Path

import pytest

from collector.market import unemployment
from collector.sources.kosis import parse
from collector.sources.molit import ApiError

FIX = Path(__file__).parent / "fixtures" / "kosis_unemp_sample.json"


def test_parse_sample():
    pts = parse(json.loads(FIX.read_text()))   # 2026-01~08 계절조정 실업률 실제 응답
    assert len(pts) == 8 and pts[0] == ("202601", 3.0) and pts[-1] == ("202608", 2.7)


def test_parse_errors():
    assert parse({"err": "30", "errMsg": "데이터가 존재하지 않습니다."}) == []
    with pytest.raises(ApiError):
        parse({"err": "11", "errMsg": "인증키 오류"})


def test_unemployment_bands_and_b4():
    u = unemployment(parse(json.loads(FIX.read_text())))
    assert (u.period, u.rate, u.chg_3m, u.band, u.b4_met) == ("202608", 2.7, -0.1, "안정", False)
    assert unemployment([("202601", 3.0), ("202602", 3.1), ("202603", 3.3), ("202604", 3.5)]).b4_met   # 3개월 +0.5%p
    assert unemployment([("202601", 4.1)]).band == "경기침체" and unemployment([("202601", 4.1)]).b4_met
    assert unemployment([("202601", 6.0)]).band == "경제 위기"
    assert unemployment([]) is None


def test_from_year_to_date():
    from collector.sources.kosis import from_year_to_date
    cum = [("202511", 90.0), ("202512", 100.0), ("202601", 10.0), ("202602", 25.0), ("202604", 50.0)]
    assert from_year_to_date(cum) == [("202512", 10.0), ("202601", 10.0), ("202602", 15.0)]   # 3월이 빠져 4월은 버림
