"""손 관리 사실(정책 이력·철도·신도시)의 출처 등급·확인일 점검 (2026-11-10). site.yml 이 화면 만들기 전에 돌려서, 실패하면 어제 사이트 그대로."""

import re
from datetime import date

from collector.newtowns import NEWTOWNS, mismatches, presale_sql
from collector.policy import EVENT_MORE, EVENTS, UPCOMING, ZONES
from collector.projects import PROJECTS
from collector.provenance import CUTOFF, grade, outlet, stale
from collector.regions import REGIONS

URL = re.compile(r"^https?://[^\s/]+\.[^\s/]+")


def test_grade_and_outlet():
    assert outlet("https://m.inews24.com/v/1") == outlet("https://www.inews24.com/x") == "inews24.com"
    assert outlet("https://biz.heraldcorp.com/a") == "heraldcorp.com" and outlet("http://www.hanamilbo.net/n") == "hanamilbo.net"
    assert outlet("https://www.kihoilbo.co.kr/n") == "kihoilbo.co.kr"
    assert grade(["https://www.molit.go.kr/x"]) == "B" and grade(["https://www.korea.kr/x", "https://a.com"]) == "B"
    assert grade(["https://www.fnnews.com/a", "https://m.fnnews.com/b"]) == "D"     # 같은 언론사 두 번은 1곳
    assert grade(["https://www.fnnews.com/a", "https://www.sedaily.com/b"]) == "C"


def test_every_hand_fact_has_source_and_date():
    today = date.today()
    for p in PROJECTS:
        assert all(URL.match(u) for u in p.sources), p.name
        assert p.checked <= today, p.name
    for t in NEWTOWNS:
        assert all(URL.match(u) for u in t.sources), t.name
        assert t.checked <= today, t.name
    for d, k, title, src in EVENTS:
        assert URL.match(src), title
    for z in ZONES:
        assert URL.match(z.source), z.note
    for d, k, title, src in UPCOMING:
        assert URL.match(src), title


def test_new_facts_are_cross_checked():
    """CUTOFF 이후 넣거나 고친 칸은 기사 1곳(D) 금지: 정부 발표(B)나 서로 다른 언론사 2곳(C) 이상."""
    for p in PROJECTS:
        if p.checked >= CUTOFF:
            assert grade(p.sources) in "BC", p.name
    for t in NEWTOWNS:
        if t.checked >= CUTOFF:
            assert grade(t.sources) in "BC", t.name
    keys = {(d, k) for d, k, _, _ in EVENTS}
    for (d, k), (more, checked) in EVENT_MORE.items():
        assert (d, k) in keys and all(URL.match(u) for u in more), (d, k)
    for d, k, _, src in EVENTS:
        if d >= CUTOFF:
            assert (d, k) in EVENT_MORE and grade((src, *EVENT_MORE[(d, k)][0])) in "BC", (d, k)


def test_newtown_fields():
    stages = {"발표", "지구지정", "착공", "입주"}
    for t in NEWTOWNS:
        assert t.stage in stages and all(c in REGIONS for c in t.region_codes), t.name
        assert t.first_move_in is None or re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", t.first_move_in), t.name
        assert re.fullmatch(r"[\d.~]+만", t.homes), t.name
    assert len({t.name for t in NEWTOWNS}) == len(NEWTOWNS)
    assert presale_sql() and presale_sql().count("UNION ALL") == sum(1 for t in NEWTOWNS if t.ps_kw) - 1


def test_mismatch_and_stale():
    first = next(t for t in NEWTOWNS if t.first_move_in)
    y, m = first.first_move_in.split("-")
    assert mismatches({first.name: [y + m, y + m, 1, 100]}) == []
    assert mismatches({first.name: ["209901", "209901", 1, 100]}) == [f"{first.name}: 손 값 {first.first_move_in} ↔ 공고 첫 입주 2099-01"]
    assert mismatches({}) == []
    assert stale([("a", date(2026, 1, 1)), ("b", date(2026, 11, 1))], date(2026, 11, 10)) == [("a", date(2026, 1, 1))]


def test_weekly_check_lines():
    from jobs.notify import check_lines

    class _Db:
        def __init__(self, rows): self.rows = rows
        def query(self, sql): return self.rows

    t = next(x for x in NEWTOWNS if x.first_move_in)
    ok = [{"nt": t.name, "a": t.first_move_in.replace("-", ""), "b": "203001", "n": 2, "hh": 900}]
    assert check_lines(_Db(ok), CUTOFF) == []                                   # 손 값 = 공고, 갓 확인
    bad = [{**ok[0], "a": "209901"}]
    assert any("2099-01" in x for x in check_lines(_Db(bad), CUTOFF))
    assert any(x.startswith("🔎 다시 확인") for x in check_lines(_Db(ok), date(2027, 6, 1)))   # 90일 넘음
