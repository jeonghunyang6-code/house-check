"""관심 단지 재건축·리모델링 진행 단계 (2026-11-15 사용자 요청: 기사 목록 대신 '지금 몇 단계인지').

리모델링은 공공데이터가 없어(서울시도 단지 목록 미공개) 손으로 관리한다(이 파일). 재건축·재개발은 서울 정비사업 공공데이터(jobs/redev.py)가 따로 있다.
손 관리 사실 규칙(CLAUDE.md, collector/provenance.py): 단계 날짜마다 구청·서울시 발표 또는 서로 다른 언론사 2곳 이상. 못 찾은 단계는 넣지 않는다.

자동 갱신(jobs/remodel.py, 매일): 관심 단지 이름이 제목에 있는 기사(jobs/complex_news.py → complex_news)에서
  '단계 말 + 끝난 말'(통과·인가·승인·선정·착공 …)이 한 마디 안에 있고 '안 끝난 말'(앞두고·신청·예정·연기·무산 …)이 없는 제목을
  서로 다른 언론사 🔧3곳 이상이 🔧3일 안에 보도하면 그 단계로 올린다(앞으로만, remodel_auto 0086). 화면엔 '자동', 금요일 요약에 알림,
  틀리면 텔레그램 답장 '빼줘'(web/lib/tgreply.js). 뒤로 가는 일(무산·취소)은 자동으로 바꾸지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

STAGES = ("추진위", "조합설립", "시공사", "안전진단", "도계위", "건축심의", "사업승인", "이주", "착공", "준공")
STAGE_RX = {
    "추진위": r"추진위",
    "조합설립": r"조합\s?설립|조합\s?인가",
    "시공사": r"시공사|시공자|시공권",
    "안전진단": r"안전진단",
    "도계위": r"도시계획\s?(위원회|심의)|도계위|도시[·ㆍ]?건축\s?공동\s?위|경관\s?심의|지구단위",
    "건축심의": r"건축\s?심의|건축\s?위원회",
    "사업승인": r"사업계획\s?승인|행위\s?허가|권리\s?변동",
    "이주": r"이주",
    "착공": r"착공",
    "준공": r"준공",
}
REVIEW = r"심의"   # 어떤 심의인지 안 적은 '서울시 심의 통과' → 아직 안 지난 심의 단계(도계위 → 건축심의) 중 앞의 것
DONE = r"통과|가결|인가|승인|선정|확정|완료|받아|받았|받은|마쳐|마쳤|돌입|개시|시작|착수|출범|결성|발족"
NOT_YET = r"앞두|신청|예정|검토|연기|무산|취소|철회|불발|보류|부결|재심의|목표|전망|위해|할\s?계획|계획이다|추진한다|추진\s?중|난항|지연|반려|\?"
MIN_PRESS = 3   # 🔧 서로 다른 언론사
SAME_DAYS = 3   # 🔧


@dataclass(frozen=True)
class Step:
    stage: str
    d: str                       # 'YYYY-MM-DD' 또는 'YYYY-MM'
    note: str
    sources: tuple[str, ...]
    checked: date = date(2026, 11, 15)


@dataclass(frozen=True)
class Remodel:
    kind: str                    # 리모델링 / 재건축
    steps: tuple[Step, ...]
    next: str = ""


# 2026-11-15 확인(웹 검색, 단계마다 2곳 이상). 1차 안전진단 날짜는 부동산 정보 사이트 한 곳뿐이라 넣지 않음(뒤 단계가 지나 막대는 지난 것으로 칠함)
REMODELS: dict[str, Remodel] = {
    "11740-91": Remodel("리모델링", (   # 선사현대(암사동 509, 2,938세대, 2000년)
        Step("조합설립", "2021-09-30", "강동구 조합설립인가",
             ("https://www.hankyung.com/realestate/article/202204248086i", "https://medigatenews.com/stand/34847")),   # 한경(2022-04 '2021년 9월 인가')·아시아경제 전재
        Step("시공사", "2022-04-23", "롯데건설·현대건설 컨소시엄 선정",
             ("https://www.hankyung.com/realestate/article/202204248086i", "https://www.etoday.co.kr/news/view/2127118",
              "http://www.housingherald.co.kr/news/articleView.html?idxno=43435")),
        Step("도계위", "2024-09-27", "강동구 도시계획위원회 원안 가결",
             ("https://www.gangdong.go.kr/web/newportal/press/13862", "https://www.newsis.com/view/NISX20241010_0002915382",
              "https://www.newspim.com/news/view/20241010000512")),
        Step("건축심의", "2026-11-11", "서울시 건축심의 통과 · 최고 35층 3,206세대",
             ("https://www.newsis.com/view/NISX20261111_0003863350", "https://www.yna.co.kr/view/AKR20261111062100004",
              "https://www.seoulapt.co.kr/news/articleView.html?idxno=1602", "https://dpnews.co.kr/news/articleView.html?idxno=2748")),
    ), next="사업계획승인(행위허가)"),
    "11740-129": Remodel("리모델링", (   # 성내삼성(1999년, 1,220세대)
        Step("추진위", "2024-09", "조합설립 추진위원회 활동(소유주 설명회)",
             ("https://news.bizwatch.co.kr/article/real_estate/2024/09/09/0029", "http://www.arunews.com/news/articleView.html?idxno=29901")),
    ), next="조합설립인가(소유자 동의 3분의 2 이상)"),
}


# 확인했는데 재건축·리모델링 추진 기록이 없는 관심 단지(2010년 이전 준공) → 금요일 요약 '단계 확인 필요'에서 뺀다. 확인한 날
CHECKED_NONE: dict[str, date] = {
    "11740-3": date(2026, 11, 15),   # 명일GS(1999): 웹 검색 기사·리모델링 목록에 추진 기록 없음
    "11740-2664": date(2026, 11, 15),   # 프라이어팰리스(2007): 추진 기록 없음(2021 암사·명일 지구단위계획 특별계획구역 보도만, 뉴스핌 20210426001097)
}
OLD_YEAR = 2010   # 이 해 이하 준공 관심 단지는 단계 확인 대상(리모델링 연한 15년)


def idx(stage: str) -> int:
    return STAGES.index(stage)


def title_stage(title: str, passed: int) -> int | None:
    """제목 한 줄 → 끝난 단계 번호(없으면 None). passed = 이미 지난 단계 번호(-1 = 없음). 마디(…·,) 단위로 본다."""
    best = None
    for seg in re.split(r"…|\.\.\.|·|,|;|\||/", title or ""):
        if not re.search(DONE, seg) or re.search(NOT_YET, seg):
            continue
        hits = [idx(s) for s, rx in STAGE_RX.items() if re.search(rx, seg)]
        if not hits and re.search(REVIEW, seg):
            hits = [i for i in (idx("도계위"), idx("건축심의")) if i > passed][:1]
        if hits:
            best = max(best if best is not None else -1, max(hits))
    return best


def detect(rows: list[dict], passed: int) -> list[dict]:
    """rows: 그 단지 제목 기사 {title, outlet, url, pub}. → 새 단계 후보 [{stage, first, press, urls}] (passed 보다 앞, 언론사 MIN_PRESS 이상·SAME_DAYS 안)."""
    by: dict[int, list[dict]] = {}
    for r in rows:
        s = title_stage(r["title"], passed)
        if s is not None and s > passed:
            by.setdefault(s, []).append(r)
    out = []
    for s, rs in sorted(by.items()):
        rs = sorted(rs, key=lambda r: r["pub"])
        for i, r0 in enumerate(rs):
            win = [r for r in rs[i:] if (r["pub"] - r0["pub"]).days <= SAME_DAYS]
            press = sorted({r["outlet"] for r in win})
            if len(press) >= MIN_PRESS:
                out.append({"stage": STAGES[s], "first": r0["pub"], "press": press, "urls": [r["url"] for r in win][:5]})
                break
    return out
