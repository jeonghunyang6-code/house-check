from datetime import date, timedelta

from collector.balloon import changes, events, group_path, groups, name_region, path, sgg_adjacency, shares, verdict
from collector.policy import DTN3, GANGNAM4, GG12, SEOUL, ZONES
from collector.regions import REGIONS


def test_name_region():
    assert name_region("경기도 광주시 남종면", REGIONS) == [c for c, n in REGIONS.items() if n == "경기 광주시"][0]
    assert name_region("경기도 수원시 영통구 매탄1동", REGIONS) == "41117"
    assert name_region("서울특별시 송파구 잠실2동", REGIONS) == "11710"
    assert name_region("인천광역시 서구 검암경서동", REGIONS) is None     # 2026-07 개편 전 이름
    assert name_region("부산광역시 중구 중앙동", REGIONS) is None


def test_events_from_policy():
    ev = {d: (new, after) for d, new, after in events(ZONES)}
    assert set(ev) == {date(2025, 3, 24), date(2025, 10, 20), date(2026, 7, 5)}
    assert ev[date(2025, 3, 24)][0] == set(GANGNAM4)
    new, after = ev[date(2025, 10, 20)]
    assert new == (set(SEOUL) | set(GG12)) - set(GANGNAM4) and after == set(SEOUL) | set(GG12)
    assert ev[date(2026, 7, 5)][0] == set(DTN3)                          # 동탄·기흥·구리 토허


def test_groups_and_adjacency():
    adj = sgg_adjacency([("d1", "d2"), ("d2", "d3"), ("d3", "d4"), ("d1", "d5")],
                        {"d1": "A", "d2": "B", "d3": "C", "d4": "D", "d5": "A"})
    assert adj == {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C"}}
    g = groups({"B"}, {"A", "B"}, {"A", "B", "C", "D"}, adj)
    assert g == {"B": "inside", "C": "adjacent", "D": "far"}      # A 는 원래 규제라 뺀다


def _weekly(start, vals):
    return [(start + timedelta(days=7 * i), v) for i, v in enumerate(vals)]


def test_changes_and_path():
    s = _weekly(date(2025, 3, 3), [100, 100, 101] + [102 + i for i in range(20)])   # 3/3, 3/10, 3/17(기준) ...
    c = changes(s, date(2025, 3, 24))
    assert c["base_date"] == date(2025, 3, 17) and c["chg_4w"] == round((105 / 101 - 1) * 100, 2)   # 4/14
    assert c["chg_26w"] is None and c["weeks_now"] == 20
    s2 = [x for x in s if x[0] != date(2025, 4, 14)]                  # 발표 없는 주는 앞 주 값으로
    assert changes(s2, date(2025, 3, 24))["chg_4w"] == round((104 / 101 - 1) * 100, 2)
    p = path(s, date(2025, 3, 24), 3)
    assert list(p) == [0, 1, 2, 3] and p[0] == 0
    gp = group_path({"A": {0: 0.0, 1: 1.0}, "B": {0: 0.0, 1: 3.0}, "C": {0: 0.0}}, {"A": "adjacent", "B": "adjacent", "C": "far"})
    assert ("adjacent", 1, 2.0, 2) in gp and ("far", 0, 0.0, 1) in gp


def test_shares():
    m = {"202502": {"total": 100, "same_sgg": 60, "seoul": 10}, "202504": {"total": 50, "same_sgg": 20, "seoul": 20}}
    s = shares(m, date(2025, 3, 24))
    assert s == {"outsider_before": 40.0, "seoul_before": 10.0, "outsider_after": 60.0, "seoul_after": 40.0}


def test_until_and_verdict():
    s = _weekly(date(2025, 3, 3), [100, 100, 101] + [102 + i for i in range(20)])
    c = changes(s, date(2025, 3, 24), until=date(2025, 4, 21))      # 4/14 까지만
    assert c["weeks_now"] == 4 and c["chg_13w"] is None
    assert changes(s, date(2026, 1, 1)) is None                      # 사건 뒤 자료 없음
    assert verdict(7.5, 5.1, 0.1, 0.5) == "번짐(붙은 바깥도 오름)"
    assert verdict(2.0, 3.0, 0.0, 0.5) == "풍선(바깥이 규제지역보다 더 오름)"
    assert verdict(2.0, 0.3, 0.0, 0.5) == "번짐 없음" and verdict(None, 1, 1, 0.5) is None
