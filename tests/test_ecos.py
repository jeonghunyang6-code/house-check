import json
from pathlib import Path

import pytest

from collector.market import loan_growth, mortgage_band
from collector.sources.ecos import parse
from collector.sources.molit import ApiError

FIX = Path(__file__).parent / "fixtures" / "ecos_mortgage_sample.json"


def test_parse_sample():
    pts = parse(json.loads(FIX.read_text()))   # 2026-01~08 예금은행 주담대 금리 실제 응답
    assert pts[-1] == ("202608", 4.66) and [p for p, _ in pts] == sorted(p for p, _ in pts)


def test_parse_errors():
    assert parse({"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}) == []
    with pytest.raises(ApiError):
        parse({"RESULT": {"CODE": "ERROR-100", "MESSAGE": "인증키가 유효하지 않습니다."}})


def test_mortgage_band():
    assert mortgage_band(2.9) == "3% 미만" and mortgage_band(4.66) == "3~5% (심리적 한계 구간)"
    assert mortgage_band(5.0) == "5~7% (한계 초과)" and mortgage_band(7.1) == "7% 이상 (체감 급변)"


def _ms(vals):
    return [(f"{2025 + i // 12}{i % 12 + 1:02d}", v) for i, v in enumerate(vals)]


def test_loan_growth():
    # 잔액 100 → 매달 +1: 전년비가 점점 줄어든다 (12/100 > 12/103)
    g = loan_growth(_ms([100 + i for i in range(16)]))
    assert g.yoy == round(12 / 103 * 100, 2) and g.yoy_chg_3m < 0 and g.state == "둔화"
    up = loan_growth(_ms([100 * 1.01 ** (i * i / 10) for i in range(16)]))   # 증가 속도가 빨라짐
    assert up.state == "확대"
    assert loan_growth(_ms([100] * 13)).state == "비교 불가" and loan_growth(_ms([100] * 12)) is None


def test_rebase_2005():
    from collector.market import rebase
    monthly = [("200412", 90.0), ("200501", 99.0), ("200512", 101.0), ("202601", 300.0)]
    assert rebase(monthly) == [("200501", 99.0), ("200512", 101.0), ("202601", 300.0)]   # 2005 평균 100
    assert rebase([("2004", 5.0), ("2005", 50.0), ("2025", 175.0)]) == [("2005", 100.0), ("2025", 350.0)]
    assert rebase([("2010", 1.0)]) == []


def test_rate_price_relation():
    from collector.market import rate_price_relation, yoy_series
    ms = [f"{2024 + i // 12}{i % 12 + 1:02d}" for i in range(24)]
    price = [(m, 100 + i) for i, m in enumerate(ms)]                 # 계속 상승
    rate = [(m, 3.0 if i < 12 else (3.5 if i < 18 else 3.0)) for i, m in enumerate(ms)]
    assert yoy_series(price)[0] == ("202501", 12.0)
    rel = dict(rate_price_relation(rate, price))
    assert rel["202501"] == "동행"        # 금리 +0.5 (1년 전 3.0 → 3.5), 집값 상승
    assert rel["202507"] == "금리 동결"    # 3.0 → 3.0
    down = [(m, 3.0 - (0.5 if i >= 12 else 0)) for i, m in enumerate(ms)]
    assert dict(rate_price_relation(down, price))["202503"] == "역행"   # 금리 인하기에 집값 상승
