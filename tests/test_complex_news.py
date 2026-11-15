from datetime import date

from collector import complex_news as C


def test_names():
    assert C.core_name("선사현대아파트") == "선사현대"
    assert C.core_name("위례24단지(꿈에그린)") == "위례24단지"
    assert C.core_name("미사강변 골든 센트로") == "미사강변골든센트로"
    assert C.names_of("11740-3", "명일지에스아파트") == ("명일지에스", "명일GS")


def test_matches_and_title():
    n, pl = ("선사현대",), ("암사동", "암사", "강동구", "강동")
    assert C.matches("암사동 선사 현대 아파트 리모델링 심의 통과", n, pl)          # 띄어 써도
    assert not C.matches("선사현대 리모델링 심의 통과", n, pl)                       # 4글자 이하: 동·구 이름 없으면 뺌
    assert C.matches("래미안솔베뉴 49㎡ 17억", ("래미안솔베뉴",), ())
    assert not C.matches("구립래미안솔베뉴어린이집(명일동) 시간제 보육", ("래미안솔베뉴",), ())   # 시설 이름만
    assert C.in_title("선사현대, 3206가구로 리모델링", n) and not C.in_title("망우동 상생주택 공급", n)


def test_tags_and_press():
    assert C.tags_of("선사현대 리모델링 시공사 롯데") == ["리모델링", "시공사"]
    assert C.tags_of("전용 84㎡ 22억5000만원에 거래됐다") == ["거래"]
    assert C.press_name("https://www.hankyung.com/article/1") == "한국경제"
    assert C.press_name("https://www.newswhoplus.com/news/1") == "newswhoplus"


def test_group_same_story():
    r = lambda t, u, o, d, it=False, tg=(): {"title": t, "url": u, "outlet": o, "pub": d, "in_title": it, "tags": list(tg)}
    rows = [r("서울시, 망우동 상생주택·선사현대 리모델링 심의 통과…392가구 공급", "a", "뉴시스", date(2026, 11, 11), True, ["리모델링"]),
            r("망우동 상생주택·선사현대아파트 리모델링 서울시 심의 통과", "b", "아유경제", date(2026, 11, 11), True, ["리모델링"]),
            r("망우동 옛 터미널에 124가구 주택…선사현대 리모델링으로 268가구 늘어", "c", "서울신문", date(2026, 11, 12), True, ["리모델링", "이주"]),
            r("강동구 반려식물 클리닉 연말까지 운영", "d", "데일리안", date(2026, 9, 21))]
    g = C.group(rows)
    assert len(g) == 2 and g[0]["others"] == 2 and g[0]["title"].startswith("서울시") and g[0]["tags"] == ["리모델링", "이주"]
    assert g[1]["url"] == "d" and g[1]["others"] == 0
