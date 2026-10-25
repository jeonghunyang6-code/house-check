from datetime import date

from collector.sources.molit import parse_right_page
from jobs.right_deals import keyed, months_back

# 2026-10-21 실제 응답 모양(강동구) 줄임
XML = """<?xml version="1.0" encoding="utf-8"?><response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header><body><items>
<item><aptNm>더샵 강동센트럴시티</aptNm><cdealDay> </cdealDay><cdealType> </cdealType><dealAmount>126,000</dealAmount><dealDay>19</dealDay><dealMonth>9</dealMonth><dealYear>2025</dealYear><dealingGbn>중개거래</dealingGbn><excluUseAr>59.9958</excluUseAr><floor>14</floor><jibun>410-100</jibun><ownershipGbn>입</ownershipGbn><sggCd>11740</sggCd><umdNm>천호동</umdNm></item>
<item><aptNm>더샵 강동센트럴시티</aptNm><cdealDay> </cdealDay><cdealType> </cdealType><dealAmount>126,000</dealAmount><dealDay>19</dealDay><dealMonth>9</dealMonth><dealYear>2025</dealYear><dealingGbn>중개거래</dealingGbn><excluUseAr>59.9958</excluUseAr><floor>14</floor><jibun>410-100</jibun><ownershipGbn>입</ownershipGbn><sggCd>11740</sggCd><umdNm>천호동</umdNm></item>
<item><aptNm>비오르(VIORR)</aptNm><cdealDay>26.10.02</cdealDay><cdealType>O</cdealType><dealAmount>178,800</dealAmount><dealDay>30</dealDay><dealMonth>9</dealMonth><dealYear>2026</dealYear><dealingGbn>직거래</dealingGbn><excluUseAr>84.6231</excluUseAr><floor>15</floor><jibun>356</jibun><ownershipGbn> </ownershipGbn><sggCd>11740</sggCd><umdNm>천호동</umdNm></item>
</items><numOfRows>100</numOfRows><pageNo>1</pageNo><totalCount>3</totalCount></body></response>"""


def test_parse_right_page():
    rows, total = parse_right_page(XML)
    assert total == 3 and len(rows) == 3
    a, _, c = rows
    assert (a.kind, a.price_10k, a.area_group, a.floor, a.contract_date, a.deal_type) == ("입주권", 126000, 59, 14, date(2025, 9, 19), "중개")
    assert c.kind == "분양권" and c.is_cancelled and c.cancel_date == date(2026, 10, 2) and c.deal_type == "직거래"


def test_keyed_and_months():
    rows, _ = parse_right_page(XML)
    keys = [k for k, _ in keyed(rows)]
    assert keys[0].endswith("#1") and keys[1].endswith("#2") and keys[0][:-2] == keys[1][:-2]   # 같은 값 두 건은 순번으로
    assert "더샵강동센트럴시티" in keys[0]                                                        # 이름 띄어쓰기 무시
    assert months_back(date(2026, 2, 5), 3) == ["202602", "202601", "202512"]


def test_nums_guard():
    from jobs.right_deals import _norm, _nums
    assert _nums(_norm("제일풍경채 검단Ⅰ")) != _nums(_norm("제일풍경채 검단Ⅲ 본청약"))      # lower() 뒤에도 로마 숫자 구분
    assert _nums(_norm("브레인시티2BL로제비앙")) == _nums(_norm("평택 브레인시티 2BL 대광로제비앙"))
