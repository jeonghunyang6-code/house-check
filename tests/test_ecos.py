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
