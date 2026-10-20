"""정책 발표 감지: 네이버 뉴스 제목·요약문에서 '새로 결정된' 부동산 정책을 찾아 후보로 올린다 (jobs/policy_news.py → policy_news 0067).

2026-10-20 동탄·기흥·구리 규제(6-30 발표)가 정책 이력에 빠진 일로 만듦. 자동으로 정책 이력(collector/policy.py)에 넣지 않는다:
기사만으로는 대상 지역·효력일을 틀리게 읽을 수 있어 사람이 확인한 뒤 policy.py 에 넣는다.

판정은 문장 단위(기사 본문은 열지 않음):
  결정 문장 = 정책 종류 말 + 결정 동사(지정한다·지정하기로·해제됐다·시행한다고 …) + 날짜 단서(기사 날·전날의 'N일', 이날·내일, '~부터')
              + 지난 일·추측 말(지난해·이후·검토·가능성·요구 …)이 없음
  후보 = 같은 종류의 결정 기사가 서로 다른 언론사 3곳 이상 🔧(2026-10-21 과거 발표 3건·최근 기사로 시험해 정함)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from urllib.parse import urlparse

from collector.policy import EVENTS, SEOUL
from collector.regions import REGIONS

KINDS = {
    "토허": r"토지거래\s?허가|토허",
    "규제지역": r"조정대상지역|투기과열지구|규제지역",
    "대출": r"LTV|DSR|주담대|주택담보대출|대출\s?한도|대출\s?규제",
    "세금": r"양도세|양도소득세|종부세|종합부동산세|보유세|취득세|세제\s?개편",
    "공급": r"공급\s?대책|공급\s?확대\s?방안|공급\s?방안|신규\s?택지|용적률",
}
ACT = r"지정|해제|연장|확대|축소|강화|완화|상향|하향|시행|도입|폐지|유예|재시행|중과|발표|확정|의결"
# '지정한다·지정하기로·지정키로·지정했다·지정됐다·지정한다고·시행된다' 꼴. '지정된 지·지정했지만' 은 안 걸린다
FRESH = re.compile(rf"({ACT})\s?(한다|된다|하기로|키로|했다|됐다|한다고|했다고|된다고|됐다고|할\s?방침|하겠다)")
STALE = re.compile(r"앞서|지난해|작년|지난\s?\d+월|올해\s?\d+월|지난달|이후|이래|당시|지났|검토|가능성|요구|촉구|전망|관측|거론|기로|여부|충족|"
                   r"우려|논의|할지|할까|될까|될지|듯|만약|주장|제안|요청|건의|촉각|했지만|됐지만|에도")
SOON = re.compile(r"오늘|내일|이날|부터")
SPLIT = re.compile(r"(?<=[.!?])\s+|\.\.\.|…")
MIN_PRESS = 3        # 🔧 서로 다른 언론사 수
NEAR_KNOWN = 10      # 이미 아는 사건(EVENTS)과 같은 종류로 ±10일 안이면 '이미 있음'


AMBIG = {"광주", "중원", "남동", "강화", "동안", "수정", "연수", "수지", "만세", "소사", "상록", "단원", "장안", "중랑"}   # 흔한 낱말과 같은 줄임


def _aliases() -> list[tuple[str, str]]:
    """'서울 강남구' → 강남구·강남, '경기 화성시 동탄구' → 동탄구·동탄. 두 글자 미만 줄임은 버린다(중·서·동 …)."""
    out = []
    for code, name in REGIONS.items():
        if not code.startswith(("11", "41", "28")):
            continue
        last = name.split()[-1]
        if len(last) >= 3:   # 중구·서구·동구 같은 두 글자는 다른 말에 섞여 버린다
            out.append((last, code))
        stem = last[:-1] if last[-1] in "시구군" else last
        if len(stem) >= 2 and stem not in AMBIG:
            out.append((stem, code))
    return sorted(out, key=lambda x: -len(x[0]))


ALIASES = _aliases()
SEOUL_ALL = re.compile(r"서울\s?전역|서울\s?전\s?지역|서울\s?25개\s?(자치)?구")


def regions(sentence: str) -> set[str]:
    got = set(SEOUL) if SEOUL_ALL.search(sentence) else set()
    for a, code in ALIASES:
        if re.search(rf"(?<![가-힣]){a}", sentence):   # '투기과열지구로' 의 '구로' 같은 낱말 속 글자는 빼기
            got.add(code)
    return got


def decisions(text: str, pub: date) -> dict[str, set[str]]:
    """기사 글자 → {정책 종류: 언급 지역 코드}. 결정 문장이 없으면 빈 사전."""
    days = {pub.day, (pub - timedelta(days=1)).day}
    months = {pub.month, pub.month % 12 + 1}
    day_re = re.compile(r"(?<!\d)(" + "|".join(str(d) for d in days) + r")일")
    out: dict[str, set[str]] = {}
    for s in SPLIT.split(text):
        if STALE.search(s) or not FRESH.search(s) or not (day_re.search(s) or SOON.search(s)):
            continue
        if any(int(m) not in months for m in re.findall(r"(\d{1,2})월\s?\d{1,2}일", s)):   # '7월 1일부터 지정했다'(10월 기사) = 지난 일
            continue
        for k, pat in KINDS.items():
            if re.search(pat, s):
                out.setdefault(k, set()).update(regions(s))
    return out


@dataclass
class Cand:
    kind: str
    first: date
    press: set[str] = field(default_factory=set)
    titles: list[tuple[date, str, str]] = field(default_factory=list)   # (날짜, 글, 주소)
    region_hits: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    known: str | None = None

    def region_codes(self) -> list[str]:
        """두 기사 이상에서 나온 지역만(한 기사만 말한 지역은 잡음이 많다)."""
        return sorted(c for c, n in self.region_hits.items() if n >= 2)


def press_of(url: str) -> str:
    h = urlparse(url or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def candidates(articles: list[dict], today: date, days: int = 3) -> list[Cand]:
    """최근 days 일 기사 → 종류별 후보(언론사 MIN_PRESS 곳 이상). 아는 사건과 겹치면 known 에 그 제목."""
    by: dict[str, Cand] = {}
    seen = set()
    for a in sorted(articles, key=lambda a: a["pub"]):
        if not today - timedelta(days=days - 1) <= a["pub"] <= today or a["id"] in seen:
            continue
        seen.add(a["id"])
        for k, regs in decisions(a["text"], a["pub"]).items():
            c = by.setdefault(k, Cand(k, a["pub"]))
            p = press_of(a["id"])
            if p in c.press:
                continue
            c.press.add(p)
            c.titles.append((a["pub"], a["text"][:160], a["id"]))
            for r in regs:
                c.region_hits[r] += 1
    out = []
    for c in by.values():
        if len(c.press) < MIN_PRESS:
            continue
        for d, k, t, _ in EVENTS:
            if k == c.kind and abs((d - c.first).days) <= NEAR_KNOWN:
                c.known = f"{d} {t}"
        out.append(c)
    return sorted(out, key=lambda c: (c.first, c.kind))

# 매일 부르는 검색어(최신순). 종류마다 지정·해제·발표 쪽 말을 섞는다
QUERIES = ("토지거래허가구역 지정", "토지거래허가구역 해제", "토지거래허가구역 연장", "조정대상지역 지정", "투기과열지구 지정", "규제지역 해제",
           "부동산 대책 발표", "주택담보대출 규제 발표", "LTV DSR 규제", "양도세 중과", "부동산 세제 개편", "주택 공급 대책 발표")
