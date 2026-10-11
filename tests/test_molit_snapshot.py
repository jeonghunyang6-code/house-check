from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from collector.snapshot import apply_snapshot, keyed, open_store
from collector.sources.molit import ApiError, parse_trade_page

# 2026-10-11 공공데이터포털 실제 응답(서울 강남구 2026-08)에서 5건만 뽑은 것: 해제·직거래·등기일 있음·법인 포함
XML = (Path(__file__).parent / "fixtures" / "molit_trade_sample.xml").read_text(encoding="utf-8")


def _deals():
    deals, total = parse_trade_page(XML)
    assert total == 5
    return deals


def test_parse_cancelled_direct_and_rgst():
    deals = _deals()
    cancelled = [d for d in deals if d.is_cancelled]
    assert len(cancelled) == 1 and cancelled[0].cancel_date == date(2026, 10, 6)
    assert any(d.deal_type == "직거래" for d in deals)
    assert any(d.rgst_date is not None for d in deals)
    assert all(d.price_10k > 1000 and d.apt_seq.startswith("11680-") for d in deals)


def test_deal_key_and_area_group():
    d = _deals()[0]
    assert d.deal_key.split("|")[0] == d.apt_seq
    assert d.area_group == int(d.area_m2)


def test_error_response_raises():
    err = '<?xml version="1.0"?><OpenAPI_ServiceResponse><cmmMsgHeader><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>'
    with pytest.raises(ApiError):
        parse_trade_page(err)


def test_bootstrap_leaves_first_seen_null_then_new_deal_registered():
    con = open_store()
    deals = _deals()
    assert apply_snapshot(con, "11680", "202608", deals[:3], date(2026, 10, 11), bootstrap=True) == []
    assert con.execute("SELECT COUNT(*) FROM deals WHERE first_seen_date IS NULL").fetchone()[0] == 3
    ev = apply_snapshot(con, "11680", "202608", deals, date(2026, 10, 12))
    assert {e.event for e in ev} >= {"registered"}
    new_key = [e.deal_key for e in ev if e.event == "registered"][0]
    assert con.execute("SELECT first_seen_date FROM deals WHERE deal_key=?", (new_key,)).fetchone()[0] == "2026-10-12"


def test_cancellation_detected_once_and_disappeared_marked():
    con = open_store()
    base = [d for d in _deals() if not d.is_cancelled]
    victim = base[0]
    apply_snapshot(con, "11680", "202608", base, date(2026, 10, 11), bootstrap=True)
    ev = apply_snapshot(con, "11680", "202608", [replace(victim, is_cancelled=True, cancel_date=date(2026, 10, 12))] + base[1:], date(2026, 10, 12))
    assert [(e.event, e.deal_key) for e in ev] == [("cancelled", victim.deal_key + "#0")]
    # 같은 스냅샷을 다시 반영해도 이벤트가 중복되지 않는다
    assert apply_snapshot(con, "11680", "202608", [replace(victim, is_cancelled=True, cancel_date=date(2026, 10, 12))] + base[1:], date(2026, 10, 13)) == []
    # 한 건이 응답에서 사라지면 'disappeared' 로 한 번만 표시
    ev = apply_snapshot(con, "11680", "202608", base[1:], date(2026, 10, 14))
    assert [e.event for e in ev] == ["disappeared"]
    assert apply_snapshot(con, "11680", "202608", base[1:], date(2026, 10, 15)) == []


def test_identical_keys_are_kept_as_separate_deals():
    d = next(x for x in _deals() if not x.is_cancelled)
    dup = [d, d, replace(d, is_cancelled=True, cancel_date=date(2026, 10, 1))]
    k = keyed(dup)
    assert len(k) == 3 and [x.is_cancelled for x in k.values()] == [False, False, True]
    con = open_store()
    apply_snapshot(con, "11680", "202608", dup, date(2026, 10, 11), bootstrap=True)
    assert con.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 3
