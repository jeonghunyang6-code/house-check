from datetime import date
from pathlib import Path

import pytest

from collector.sources.molit import QuotaExceeded, parse_rent_page, parse_trade_page

# 2026-10-11 공공데이터포털 실제 응답(서울 강남구 2026-09 전월세)에서 유형별로 5건: 계약구분 공백·신규 전세·신규 월세·갱신요구권 사용·갱신
XML = (Path(__file__).parent / "fixtures" / "molit_rent_sample.xml").read_text(encoding="utf-8")


def test_parse_rent_types():
    rents, total = parse_rent_page(XML)
    assert total == 5 and len(rents) == 5
    assert [r.contract_type for r in rents].count(None) == 1
    jeonse = [r for r in rents if r.contract_type == "신규" and r.monthly_rent_10k == 0]
    assert jeonse and jeonse[0].deposit_10k > 10000
    rr = [r for r in rents if r.used_renewal_right]
    assert rr and rr[0].contract_type == "갱신" and rr[0].pre_deposit_10k is not None
    for r in rents:
        if r.contract_term:
            assert r.term_start and r.term_end and r.term_end > r.term_start
            assert r.term_start.day == 1
    assert all(r.contract_date.month == 9 and not r.is_cancelled for r in rents)


def test_rent_key_differs_by_money():
    r = parse_rent_page(XML)[0][0]
    assert r.deal_key.startswith(r.apt_seq + "|") and r.deal_key.endswith(f"|{r.deposit_10k}|{r.monthly_rent_10k}")


def test_quota_errors_stop():
    gw = ('<?xml version="1.0"?><OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>'
          'LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR</returnAuthMsg><returnReasonCode>22</returnReasonCode>'
          '</cmmMsgHeader></OpenAPI_ServiceResponse>')
    with pytest.raises(QuotaExceeded):
        parse_trade_page(gw)
    hdr = '<response><header><resultCode>22</resultCode><resultMsg>LIMIT</resultMsg></header></response>'
    with pytest.raises(QuotaExceeded):
        parse_rent_page(hdr)
