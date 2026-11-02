from datetime import date

from collector import official as O
from jobs import policy_news as J

RSS = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>\xec\x88\x98\xeb\x8f\x84\xea\xb6\x8c \xec\x8b\xa0\xea\xb7\x9c\xed\x83\x9d\xec\xa7\x80 \xed\x9b\x84\xeb\xb3\xb4\xec\xa7\x80 6\xea\xb3\xb3 \xeb\xb0\x9c\xed\x91\x9c</title><link>https://www.korea.kr/a</link><pubDate>Thu, 29 Oct 2026 10:00:00 +0900</pubDate></item>
<item><title>bad date</title><pubDate>x</pubDate></item>
</channel></rss>"""


def test_official_parse_and_match():
    items = O.parse(RSS, "dept_molit.xml")
    assert [x["d"] for x in items] == ["2026-10-29"]                     # 날짜 못 읽은 항목은 버림
    assert O.match("공급", date(2026, 10, 30), items)["u"] == "https://www.korea.kr/a"   # ±1일
    assert O.match("공급", date(2026, 11, 2), items) is None             # 날짜 밖
    assert O.match("대출", date(2026, 10, 29), items) is None            # 종류 말이 없음


def test_official_fetch_keeps_going_when_a_feed_fails():
    def opener(req, timeout=0):
        if "fsc" in req.full_url:
            raise OSError("blocked")
        class R:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return RSS
        return R()
    items, errs = O.fetch(("https://x/dept_molit.xml", "https://x/dept_fsc.xml"), opener)
    assert len(items) == 1 and len(errs) == 1 and errs[0].startswith("dept_fsc.xml")


def test_title_and_message():
    assert J.title_of("[단독] 김포·구리: 신규택지 7만가구") == "김포·구리 신규택지 7만가구"
    assert len(J.title_of("가" * 80)) == 51
    msg = J.auto_msg([{"d": "2026-10-29", "kind": "공급", "n": 12, "title": "김포 <신규>"}])
    assert "• 10/29 공급 · 언론사 12곳: 김포 &lt;신규&gt;" in msg and "빼줘" in msg


def test_promote_and_save_pg():
    """0067·0082 + save(언론사 수 최대값 유지) + promote(5곳·이틀, 같은 사건 한 번). HC_TEST_PG_URL 이 있을 때만."""
    import os
    from pathlib import Path
    from collector.db import PsqlDb, select
    from collector.policy_news import Cand
    url = os.environ.get("HC_TEST_PG_URL")
    if not url:
        return
    root = Path(__file__).parent.parent
    db = PsqlDb(url)
    db.query("DROP TABLE IF EXISTS policy_news CASCADE;")
    for m in ("0067_policy_news.sql", "0082_policy_news_auto.sql"):
        db.query((root / "db" / "migrations" / m).read_text(encoding="utf-8"))
    def cand(first, n, last, kind="공급"):
        c = Cand(kind, first)
        c.press = {f"p{i}" for i in range(n)}
        c.titles = [(first, "[단독] 신규택지 발표", "u1"), (last, "후속", "u2")]
        return c
    J.save(db, [cand(date(2026, 10, 29), 12, date(2026, 10, 30)), cand(date(2026, 10, 20), 6, date(2026, 10, 20), "대출")])
    J.save(db, [cand(date(2026, 10, 29), 4, date(2026, 10, 31))])          # 나중 실행: 3일 창이라 4곳만 보임
    row = select(db, "SELECT n_press, last_date::text l FROM policy_news WHERE kind = '공급'")[0]
    assert (int(row["n_press"]), row["l"]) == (12, "2026-10-31")
    J.save(db, [cand(date(2026, 10, 30), 7, date(2026, 10, 31))])          # 같은 사건이 첫날만 달리 한 줄 더
    got = J.promote(db, date(2026, 11, 2))
    assert [(r["kind"], r["d"]) for r in got] == [("공급", "2026-10-29")]   # 대출은 하루만 보도 → 안 됨, 10-30 줄은 같은 사건
    st = {(r["kind"], r["d"]): r["status"] for r in select(db, "SELECT kind, first_date::text d, status FROM policy_news")}
    assert st == {("공급", "2026-10-29"): "auto", ("공급", "2026-10-30"): "new", ("대출", "2026-10-20"): "new"}
    assert J.promote(db, date(2026, 11, 2)) == []                          # 두 번째 실행은 그대로
