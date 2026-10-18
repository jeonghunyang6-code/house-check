"""규제 이력: 토지거래허가구역(토허)·규제지역(조정대상지역·투기과열지구) (0043, jobs/policy.py).

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
)

EVENTS: tuple[tuple[date, str, str, str], ...] = (
    (date(2020, 6, 19), "규제지역", "6·17 대책: 경기·인천 대부분 조정대상지역, 수원·안양·용인 수지 등 경기 10곳·인천 3구 투기과열", S_2020_06),
    (date(2020, 6, 23), "토허", "잠실·삼성·대치·청담 토지거래허가", S_2020_JAMSAM),
    (date(2021, 4, 27), "토허", "압구정·여의도·목동·성수 토지거래허가", S_2021_FOUR),
    (date(2022, 11, 14), "규제지역", "서울·과천·성남 분당·수정·하남·광명 외 규제지역 해제", S_2022_11),
    (date(2023, 1, 5), "규제지역", "강남3구·용산 외 규제지역 해제", S_2023_01),
    (date(2025, 2, 13), "토허", "잠실·삼성·대치·청담 아파트 대부분 토지거래허가 해제", S_2025_02),
    (date(2025, 3, 24), "토허", "강남3구·용산 아파트 전체 토지거래허가", S_2025_03),
    (date(2025, 10, 16), "규제지역", "10·15 대책: 서울 전역·경기 12곳 규제지역", S_2025_10_REG),
    (date(2025, 10, 20), "토허", "서울 전역·경기 12곳 아파트 토지거래허가", S_2025_10_TOH),
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
