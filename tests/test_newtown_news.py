from datetime import date

from collector import newtown_news as N


def art(i, text, press="a.com", pub=date(2026, 10, 27)):
    return {"id": f"https://{press}/{i}", "text": text, "pub": pub}


def test_detects_stage_from_two_press():
    t = "일산 백송마을 1·2·3·5단지가 26일 특별정비구역으로 지정됐다. 고양시는 고시를 마쳤다"
    c = N.candidates([art(1, t, "a.com"), art(2, t, "b.com")], date(2026, 10, 27))
    assert [(x.code, x.stage) for x in c] == [("NT-일산-백송", "구역지정")]


def test_ignores_one_press_old_stage_and_other_town():
    t = "일산 백송마을이 특별정비구역으로 지정됐다"
    assert N.candidates([art(1, t)], date(2026, 10, 27)) == []                      # 언론사 1곳
    u = "분당 양지마을이 특별정비구역으로 지정됐다"                                     # 분당은 이미 구역지정
    assert N.candidates([art(1, u, "a.com"), art(2, u, "b.com")], date(2026, 10, 27)) == []
    v = "백송마을 특별정비구역 지정 검토"                                              # 신도시 이름 없음·결정 아님
    assert N.candidates([art(1, v, "a.com"), art(2, v, "b.com")], date(2026, 10, 27)) == []


def test_keys_cover_all_zones():
    from collector.newtown import ZONES
    assert set(N.KEYS) == {z.code for z in ZONES}
