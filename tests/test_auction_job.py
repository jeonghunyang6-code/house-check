from datetime import date

from jobs.auction import collect, period_of


def test_period_of():
    assert period_of(date(2026, 10, 7)) == "2026-09" and period_of(date(2026, 1, 5)) == "2025-12"


def test_collect_needs_two_articles_per_month():
    arts = [{"id": "a", "pub": date(2026, 10, 7), "text": "서울 아파트 낙찰가율은 94.7%로 집계됐다."},
            {"id": "b", "pub": date(2026, 10, 8), "text": "지난달 서울 아파트 낙찰가율은 94.7%를 기록했다."},
            {"id": "c", "pub": date(2026, 10, 9), "text": "대구 아파트 낙찰가율은 82.9%로 집계됐다. 인천 아파트 낙찰가율은 81.1%였다."},
            {"id": "d", "pub": date(2026, 9, 8), "text": "서울 아파트 낙찰가율은 93.0%로 집계됐다."}]
    got = collect(arts)
    assert got == {"2026-09": {"서울": (94.7, "a")}}     # 대구는 수도권 아님, 인천·8월은 기사 1건뿐
