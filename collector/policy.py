"""규제 이력: 토지거래허가구역(토허)·규제지역(조정대상지역·투기과열지구)·대출 규제·세금 (0043, jobs/policy.py).

📖 토허제는 거래를 줄여 상승 속도를 늦추지만 가격을 떨어뜨리진 않는다 p.269~270 / 풍선효과 p.288~292 / 지정 여부로 우열을 판단하지 마라 p.270.
쓰임: 차트 사건 표시, C4 거래 유지율 해석(토허 구역은 상승기 거래가 눌림), 풍선효과(규제 경계 안팎 비교).

- ZONES: 출처로 날짜·범위를 확인한 기간만. end=None 은 지금도 유효(2026-10-18 기준). start=None 은 2020년 이전부터
  scope: 'sgg' 시군구 전체(토허는 아파트) / 'dong' 법정동 전체 / 'part' 구역이 그 동의 일부만(단지가 들어가는지 따로 확인)
- EVENTS: 차트 표시용. 2020·2022 경기·인천 규제지역처럼 기사마다 목록이 달라 기간으로 못 넣은 것도 여기에는 있다
날짜는 2026-10-18 웹 검색으로 기사 확인(관보·고시 원문은 못 봄).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

SEOUL = ("11110", "11140", "11170", "11200", "11215", "11230", "11260", "11290", "11305", "11320", "11350", "11380", "11410",
         "11440", "11470", "11500", "11530", "11545", "11560", "11590", "11620", "11650", "11680", "11710", "11740")
GANGNAM4 = ("11680", "11650", "11710", "11170")   # 강남·서초·송파·용산
SEOUL21 = tuple(c for c in SEOUL if c not in GANGNAM4)
GG12 = ("41290", "41210", "41135", "41131", "41133", "41117", "41111", "41115", "41173", "41465", "41430", "41450")
DTN3 = ("41463", "41597", "41310")   # 용인 기흥구·화성 동탄구·구리시 (2026-06-30 지정)
GG_KEPT = ("41290", "41135", "41131", "41450", "41210")   # 2022-11-14 해제 때 남은 경기 4곳(과천·성남 분당·수정·하남·광명)

S_2020_JAMSAM = "https://kbthink.com/main/real-estate/real-estate-issue/our-house-issues/our-house-issues-230515.html"
S_2021_FOUR = "https://biz.sbs.co.kr/amp/article/20000012899"
S_2025_02 = "https://www.newsis.com/view/NISX20250212_0003063014"
S_2025_03 = "https://v.daum.net/v/20250319110519206"
S_2025_10_TOH = "https://gangdong.go.kr/web/newportal/press/14703"
S_2025_10_REG = "https://biz.sbs.co.kr/amp/article/20000266053"
S_2023_01 = "https://www.newsis.com/view/NISX20230103_0002146372"
S_2022_11 = "https://www.mt.co.kr/estate/2022/11/10/2022111006405372658"
S_2020_06 = "https://www.dailian.co.kr/news/view/898248/"
S_2026_09 = "https://news.bizwatch.co.kr/article/real_estate/2026/09/17/0033"
S_2026_06_DTN = "https://gnews.gg.go.kr/briefing/brief_gongbo_view.do?BS_CODE=S017&number=70759"
S_2026_06_REG = "https://www.khan.co.kr/article/202606300805001"
S_2026_05_TAX = "https://www.korea.kr/news/policyNewsView.do?newsId=148959488"
S_2026_05_TOH = "https://m.seoul.co.kr/news/2026/05/12/20260512500087"
S_2026_07_TAX = "https://www.fnnews.com/news/202607311725013083"


@dataclass(frozen=True)
class Zone:
    kind: str                     # '토허' | '규제지역'
    region_codes: tuple[str, ...]
    umd_names: tuple[str, ...] | None   # None = 시군구 전체
    start: date | None
    end: date | None              # 마지막 유효일
    scope: str                    # 'sgg' | 'dong' | 'part'
    note: str
    source: str


ZONES: tuple[Zone, ...] = (
    Zone("토허", ("11680",), ("삼성동", "청담동", "대치동"), date(2020, 6, 23), date(2025, 2, 12), "dong",
         "국제교류복합지구 인근. 2025-02-13 아파트 305곳 중 291곳 해제(은마 등 재건축 14곳은 유지)", S_2020_JAMSAM),
    Zone("토허", ("11710",), ("잠실동",), date(2020, 6, 23), date(2025, 2, 12), "dong",
         "국제교류복합지구 인근. 2025-02-13 대부분 해제(잠실주공5단지 등 재건축은 유지)", S_2020_JAMSAM),
    Zone("토허", ("11680",), ("압구정동",), date(2021, 4, 27), None, "part", "압구정 아파트지구", S_2021_FOUR),
    Zone("토허", ("11560",), ("여의도동",), date(2021, 4, 27), None, "part", "여의도 아파트지구와 인근", S_2021_FOUR),
    Zone("토허", ("11470",), ("목동", "신정동"), date(2021, 4, 27), None, "part", "목동 택지개발지구(걸친 동은 확인 필요)", S_2021_FOUR),
    Zone("토허", ("11200",), ("성수동1가", "성수동2가"), date(2021, 4, 27), None, "part", "성수 전략정비구역(걸친 동은 확인 필요)", S_2021_FOUR),
    Zone("토허", GANGNAM4, None, date(2025, 3, 24), None, "sgg", "강남3구·용산 아파트 전체(약 2,200단지). 2026-12-31 까지로 연장 보도", S_2025_03),
    Zone("토허", SEOUL + GG12, None, date(2025, 10, 20), None, "sgg",
         "10·15 대책, 서울 전역·경기 12곳 아파트. 고시 기간 2026-12-31(연장 여부 미정, 2026-09 보도)", S_2025_10_TOH),
    Zone("규제지역", SEOUL21, None, None, date(2023, 1, 4), "sgg", "조정대상지역·투기과열지구. 2023-01-05 해제", S_2023_01),
    Zone("규제지역", GANGNAM4, None, None, None, "sgg", "2023-01-05 해제 때도 남음", S_2023_01),
    Zone("규제지역", GG_KEPT, None, None, date(2023, 1, 4), "sgg",
         "과천·성남 분당·수정·하남·광명. 시작일은 2020년 이전 또는 2020-06-19(지역마다 다름, 확인 못 함)", S_2023_01),
    Zone("규제지역", SEOUL21 + GG12, None, date(2025, 10, 16), None, "sgg", "10·15 대책, 서울 전역·경기 12곳 조정대상지역·투기과열지구",
         S_2025_10_REG),
    # 2026-10-20 추가(사용자 질문으로 빠진 것 확인). 경기도 공고: 기흥구 81.64㎢·동탄구 55.52㎢·구리시 33.34㎢, 아파트만
    Zone("규제지역", DTN3, None, date(2026, 7, 1), None, "sgg", "용인 기흥·화성 동탄·구리 조정대상지역·투기과열지구(2026-06-30 발표, 7-01 효력)", S_2026_06_REG),
    Zone("토허", DTN3, None, date(2026, 7, 5), date(2027, 12, 31), "sgg", "용인 기흥·화성 동탄·구리 아파트 토지거래허가(2026-07-05~2027-12-31)", S_2026_06_DTN),
)

S_LOAN_2019 = "https://www.dailian.co.kr/news/view/853146/"
S_LOAN_2022 = "https://mobile.newsis.com/view/NISX20221110_0002080430"
S_LOAN_DSR3 = "https://fsc.go.kr/eng/pr010101/84620"
S_LOAN_0627 = "https://www.korea.kr/news/policyNewsView.do?newsId=148945077"
S_LOAN_1015 = "https://biz.sbs.co.kr/amp/article/20000265270"
S_LOAN_1015_JS = "https://mobile.newsis.com/view/NISX20251015_0003363513"

# 지금 적용되는 주담대 제도 상한 (시안 계산기 loanCap 과 같아야 한다). 생애최초·서민 실수요자 예외, DSR 은 넣지 않는다(은행 확인)
LOAN_RULES = {
    "asof": date(2025, 10, 16),
    "price_caps": ((150000, 60000), (250000, 40000), (None, 20000)),   # (집값 상한 만원, 대출 상한 만원) 수도권·규제지역
    "ltv": {"규제지역": 0.4, "그 밖 수도권": 0.7},
    "source": S_LOAN_1015,
}

EVENTS: tuple[tuple[date, str, str, str], ...] = (
    (date(2019, 12, 17), "대출", "12·16 대책: 투기·투기과열지구 15억 초과 아파트 주담대 금지, 9억 초과분 LTV 20%", S_LOAN_2019),
    (date(2022, 12, 1), "대출", "15억 초과 아파트 주담대 허용, 무주택·1주택 LTV 50%(12월 시행, 날짜는 1일로 둠)", S_LOAN_2022),
    (date(2025, 7, 1), "대출", "스트레스 DSR 3단계(수도권·규제지역, 가산금리 1.5%p)", S_LOAN_DSR3),
    (date(2025, 6, 28), "대출", "6·27 대책: 수도권·규제지역 주택구입 주담대 6억 한도, 6개월 안 전입, 생애최초 LTV 70%", S_LOAN_0627),
    (date(2025, 10, 16), "대출", "10·15 대책: 주담대 한도 15억 이하 6억·25억 이하 4억·초과 2억, 규제지역 LTV 40%, 스트레스 금리 하한 3%", S_LOAN_1015),
    (date(2025, 10, 29), "대출", "1주택자 수도권·규제지역 전세대출 이자 DSR 반영", S_LOAN_1015_JS),
    (date(2020, 6, 19), "규제지역", "6·17 대책: 경기·인천 대부분 조정대상지역, 수원·안양·용인 수지 등 경기 10곳·인천 3구 투기과열", S_2020_06),
    (date(2020, 6, 23), "토허", "잠실·삼성·대치·청담 토지거래허가", S_2020_JAMSAM),
    (date(2021, 4, 27), "토허", "압구정·여의도·목동·성수 토지거래허가", S_2021_FOUR),
    (date(2022, 11, 14), "규제지역", "서울·과천·성남 분당·수정·하남·광명 외 규제지역 해제", S_2022_11),
    (date(2023, 1, 5), "규제지역", "강남3구·용산 외 규제지역 해제", S_2023_01),
    (date(2025, 2, 13), "토허", "잠실·삼성·대치·청담 아파트 대부분 토지거래허가 해제", S_2025_02),
    (date(2025, 3, 24), "토허", "강남3구·용산 아파트 전체 토지거래허가", S_2025_03),
    (date(2025, 10, 16), "규제지역", "10·15 대책: 서울 전역·경기 12곳 규제지역", S_2025_10_REG),
    (date(2025, 10, 20), "토허", "서울 전역·경기 12곳 아파트 토지거래허가", S_2025_10_TOH),
    # 2026-10-20 추가(사용자 질문으로 빠진 것 확인, 웹 검색 기사 기준). 세금은 1주택 실수요자 계산에는 안 쓰고 사건 표시만
    (date(2026, 5, 10), "세금", "다주택자 양도세 중과 재시행: 유예 5월 9일 종료(그 전 계약분은 잔금 기한 예외)", S_2026_05_TAX),
    (date(2026, 5, 12), "토허", "토허 구역 실거주 의무 유예를 세입자 있는 주택 전체로 확대: 무주택 매수자, 2026-12-31까지 허가 신청, 늦어도 2028-05-11 입주", S_2026_05_TOH),
    (date(2026, 7, 1), "규제지역", "용인 기흥·화성 동탄·구리 규제지역(6-30 발표)", S_2026_06_REG),
    (date(2026, 7, 5), "토허", "용인 기흥·화성 동탄·구리 아파트 토지거래허가(~2027-12-31)", S_2026_06_DTN),
    (date(2026, 7, 31), "세금", "세제개편안: 다주택 양도세 중과 한시 완화(2주택 +20→5%p, 3주택 +30→10%p, 2028년 10·15%p), 보유세 강화. 정부안 발표 단계(입법 미확인)", S_2026_07_TAX),
)


def zones_for(region_code: str, umd_name: str | None, start: date, end: date, kind: str | None = None) -> list[Zone]:
    """[start, end] 기간에 이 단지(시군구·법정동)에 걸린 구역들. 'part' 구역은 같은 동이면 넣는다(단지가 들어가는지는 확인 필요)."""
    out = []
    for z in ZONES:
        if kind and z.kind != kind:
            continue
        if region_code not in z.region_codes:
            continue
        if z.umd_names is not None and umd_name not in z.umd_names:
            continue
        if (z.start is None or z.start <= end) and (z.end is None or z.end >= start):
            out.append(z)
    return out


def regulated_now(today: date) -> list[str]:
    """오늘 규제지역(조정대상지역·투기과열지구)인 시군구. LTV 40% 판정에 쓴다."""
    return sorted({c for z in ZONES if z.kind == "규제지역" and _on(z, today) for c in z.region_codes})


def _on(z: Zone, d: date) -> bool:
    return (z.start is None or z.start <= d) and (z.end is None or z.end >= d)
