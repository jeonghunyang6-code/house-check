from datetime import date

from collector.policy import EVENTS, GG12, SEOUL, ZONES, zones_for
from collector.regions import REGIONS


def test_codes_are_ours():
    assert sorted(SEOUL) == sorted(c for c in REGIONS if c.startswith("11"))
    assert all(c in REGIONS for z in ZONES for c in z.region_codes)
    assert len(GG12) == 12 and all(REGIONS[c].startswith("경기") for c in GG12)
    assert all(z.start is None or z.end is None or z.start <= z.end for z in ZONES)
    assert all(z.source.startswith("https://") for z in ZONES) and all(e[3].startswith("https://") for e in EVENTS)


def test_zones_for():
    up = (date(2020, 1, 1), date(2022, 1, 31))
    assert [z.note[:9] for z in zones_for("11680", "대치동", *up, kind="토허")] == ["국제교류복합지구 "]
    assert zones_for("11680", "개포동", *up, kind="토허") == []                       # 2025-03 전에는 동 단위
    assert len(zones_for("11680", "개포동", date(2025, 4, 1), date(2025, 4, 1), kind="토허")) == 1
    assert zones_for("11710", "가락동", *up, kind="토허") == []                       # 헬리오시티는 잠실동이 아님
    assert zones_for("11470", "목동", *up, kind="토허")[0].scope == "part"
    assert zones_for("41117", "영통동", date(2025, 10, 19), date(2025, 10, 19), kind="토허") == []
    assert len(zones_for("41117", "영통동", date(2025, 10, 20), date(2025, 10, 20), kind="토허")) == 1
    # 규제지역: 마포는 2023-01-05 해제, 2025-10-16 재지정
    assert zones_for("11440", None, date(2023, 6, 1), date(2025, 10, 15), kind="규제지역") == []
    assert len(zones_for("11440", None, date(2022, 1, 1), date(2022, 1, 1), kind="규제지역")) == 1


def test_loan_events_and_regulated_now():
    from collector.policy import DTN3, LOAN_RULES, regulated_now
    assert sum(1 for e in EVENTS if e[1] == "대출") == 7
    assert len({(d, k) for d, k, _, _ in EVENTS}) == len(EVENTS)      # policy_events 기본키 (날짜, 종류)
    now = regulated_now(date(2026, 10, 18))
    assert set(SEOUL) | set(GG12) | set(DTN3) == set(now)            # 10·15 서울 전역 + 경기 12곳, 2026-07 동탄·기흥·구리
    assert "11440" not in regulated_now(date(2024, 6, 1)) and "11680" in regulated_now(date(2024, 6, 1))
    assert LOAN_RULES["ltv"]["규제지역"] == 0.4 and LOAN_RULES["price_caps"][0] == (150000, 60000)


def test_projects():
    from collector.projects import PROJECTS, STATUS_ORDER, projects_for
    assert all(c in REGIONS for p in PROJECTS for c in p.region_codes)
    assert all(p.status in STATUS_ORDER and p.source.startswith("https://") for p in PROJECTS)
    assert len({p.name for p in PROJECTS}) == len(PROJECTS)
    st = [p.status for p in projects_for("11680")]
    assert st == sorted(st, key=STATUS_ORDER.index) and "확정" in st      # 강남: GTX-A·C, 위례신사선


def test_upcoming():
    from collector.policy import UPCOMING, upcoming
    assert all(u[3].startswith("https://") for u in UPCOMING)
    got = upcoming(date(2026, 10, 25))
    assert [u[0] for u in got] == [date(2026, 12, 31), date(2026, 12, 31)]   # 120일 안만
    assert upcoming(date(2027, 1, 1)) == []
