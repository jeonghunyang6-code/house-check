"""1기 신도시 선도지구 단계 변화 감지: 뉴스 제목·요약문에서 '○○마을 특별정비구역 지정됐다' 같은 문장을 찾아 후보로(2026-10-27 사용자 요청).

collector/newtown.py 의 단계는 손으로 관리 → 이 후보가 텔레그램으로 오면 기사를 확인하고 newtown.py 를 고친다(자동으로 바꾸지 않음).
판정(jobs/policy_news.py 와 같은 문장 단위): 구역 이름 + 신도시 이름(같은 기사) + 단계 말 + 결정 동사, 지난 일·추측 말 없음.
후보 = 같은 구역·단계를 서로 다른 언론사 🔧2곳 이상(지역 소식이라 정책 감지의 3곳보다 낮춤), 지금 단계보다 앞선 단계만.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from collector.newtown import ZONES
from collector.policy_news import SPLIT, STALE, press_of

# 구역 → 기사에서 찾을 이름(다른 지역과 겹치는 이름은 신도시 이름이 같은 기사에 있어야 함)
KEYS = {"NT-분당-샛별": ("샛별마을",), "NT-분당-양지": ("양지마을",), "NT-분당-시범": ("시범단지", "시범우성"),
        "NT-평촌-귀인": ("귀인블록", "꿈마을 금호", "꿈마을금호"), "NT-평촌-민백": ("민백블록", "꿈마을 우성", "꿈마을우성"), "NT-평촌-샘": ("샘마을",),
        "NT-산본-11": ("자이백합", "산본 11구역"), "NT-산본-9-2": ("한양백두", "9-2구역"), "NT-중동-은하": ("은하마을",), "NT-중동-반달A": ("반달마을",),
        "NT-일산-백송": ("백송마을",), "NT-일산-후곡": ("후곡마을",), "NT-일산-강촌": ("강촌마을", "백마마을")}
TOWN = {"분당": "분당", "평촌": "평촌", "산본": "산본", "중동": "중동", "일산": "일산"}   # 구역 코드 둘째 칸 → 기사에 있어야 할 말
STAGES = (   # (우리 단계, 번호, 기사 말)
    ("구역지정", 1, r"특별정비구역\s?(으로\s?)?지정|특별정비계획\s?결정|정비구역\s?지정\s?고시"),
    ("조합설립", 3, r"사업시행자\s?(로\s?)?지정|시행자\s?지정\s?고시|조합\s?설립\s?인가"),
    ("사업시행", 5, r"사업시행\s?(계획\s?)?인가"),
    ("관리처분", 6, r"관리처분\s?(계획\s?)?인가"),
    ("착공", 7, r"착공(식)?"),
)
DONE = re.compile(r"(지정|고시|인가|결정|착공)[을를이가]?\s?(됐|했|받았|받아|마쳤|완료|한다|된다|하기로|키로|했다고|됐다고|에 들어갔|들어간다)")
MIN_PRESS = 2   # 🔧


@dataclass
class Cand:
    code: str
    zone_nm: str
    stage: str
    stage_no: int
    press: set[str] = field(default_factory=set)
    titles: list[tuple[date, str, str]] = field(default_factory=list)


def candidates(articles: list[dict], today: date, days: int = 3) -> list[Cand]:
    now = {z.code: z for z in ZONES}
    by: dict[tuple[str, str], Cand] = {}
    seen = set()
    for a in articles:
        if not today - timedelta(days=days - 1) <= a["pub"] <= today or a["id"] in seen:
            continue
        seen.add(a["id"])
        text = a["text"]
        for code, keys in KEYS.items():
            if TOWN[code.split("-")[1]] not in text or not any(k in text for k in keys):
                continue
            for s in SPLIT.split(text):
                if not any(k in s for k in keys) or STALE.search(s) or not DONE.search(s):
                    continue
                for name, no, pat in STAGES:
                    if no > now[code].stage_no and re.search(pat, s):
                        c = by.setdefault((code, name), Cand(code, now[code].zone_nm, name, no))
                        p = press_of(a["id"])
                        if p not in c.press:
                            c.press.add(p)
                            c.titles.append((a["pub"], text[:120], a["id"]))
    return sorted((c for c in by.values() if len(c.press) >= MIN_PRESS), key=lambda c: (c.code, c.stage_no))


QUERIES = ("선도지구 특별정비구역 지정", "선도지구 사업시행자 지정", "1기 신도시 특별정비구역", "노후계획도시 특별정비구역 지정")
