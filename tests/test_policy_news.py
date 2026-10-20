from datetime import date

from collector.policy_news import candidates, decisions, regions
from jobs.policy_news import issue_md

PUB = date(2026, 6, 30)
FRESH = "국토교통부는 화성시 동탄구와 용인시 기흥구, 구리시를 조정대상지역 및 투기과열지구로 신규 지정한다고 30일 밝혔다."


def test_decisions_fresh_and_stale():
    assert decisions(FRESH, PUB) == {"규제지역": {"41597", "41463", "41310"}}
    # 지난 일·추측은 결정이 아니다
    assert decisions("지난해 10월 서울 전역이 토지거래허가구역으로 지정된 이후 전세 매물이 줄었다.", date(2026, 10, 20)) == {}
    assert decisions("앞서 국토교통부는 7월 1일부터 동탄구를 투기과열지구로 지정했다.", date(2026, 10, 6)) == {}
    assert decisions("국토교통부는 7월 1일부터 동탄구를 투기과열지구로 지정했다.", date(2026, 10, 6)) == {}   # 다른 달 날짜
    assert decisions("정부가 토허구역 연장을 검토한다고 20일 밝혔다.", date(2026, 10, 20)) == {}
    assert decisions("정부는 15일 서울 전역을 토지거래허가구역으로 지정한다고 발표했다.", date(2025, 10, 15))["토허"] >= {"11110", "11680"}


def test_regions_word_start():
    assert regions("조정대상지역 및 투기과열지구로 지정") == set()     # '지구로' 의 '구로'
    assert regions("대출 규제 강화") == set()                         # 인천 강화군 아님
    assert regions("동탄·기흥·구리") == {"41597", "41463", "41310"}


def test_candidates_threshold_and_known():
    arts = [{"id": f"https://{p}/a", "pub": PUB, "text": FRESH} for p in ("a.kr", "b.kr")]
    assert candidates(arts, PUB) == []
    arts.append({"id": "https://www.c.kr/x", "pub": PUB, "text": FRESH})
    arts.append({"id": "https://c.kr/y", "pub": PUB, "text": FRESH})        # 같은 언론사는 한 번
    (c,) = candidates(arts, PUB)
    assert c.kind == "규제지역" and len(c.press) == 3 and c.region_codes() == ["41310", "41463", "41597"]
    assert c.known and c.known.startswith("2026-07-01")                    # 정책 이력에 이미 있음
    new = candidates([{**a, "pub": date(2027, 3, 3), "text": FRESH.replace("30일", "3일")} for a in arts], date(2027, 3, 3))
    assert new and new[0].known is None
    md = issue_md(new)
    assert "규제지역 · 2027-03-03 · 언론사 3곳" in md and "경기 구리시" in md
