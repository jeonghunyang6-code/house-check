"""손으로 관리하는 사실(정책 이력·철도 사업·신도시)의 출처 등급·확인일 (2026-11-10 사용자 요청: 기사마다 숫자가 다를 때 교차검증하는 구조).

등급(출처 주소에서 자동으로 매김):
  A 공식 원자료 — 청약홈 공고·실거래·R-ONE 같은 공공 데이터. 손으로 넣지 않고 매일 대조하는 쪽(collector/newtowns.py presale_sql)
  B 정부 발표 — 출처에 정부·공공기관 주소(go.kr·korea.kr·LH)
  C 기사 2곳 이상 — 서로 다른 언론사. 숫자가 다르면 범위로 적는다
  D 기사 1곳 — CUTOFF 이후 새로 넣거나 고친 칸에는 금지(tests/test_provenance.py, site.yml 이 배포 전에 돌림). 그 전 칸은 그대로 두되 고칠 때 C 이상으로
진행 중인 사업(철도 개통 전·신도시)은 확인한 지 STALE_DAYS 🔧 가 지나면 금요일 주간 요약에 '다시 확인' 으로 뜬다.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

GRADES = {"A": "공식 원자료", "B": "정부 발표", "C": "기사 2곳 이상", "D": "기사 1곳"}
CUTOFF = date(2026, 11, 10)
STALE_DAYS = 90   # 🔧 진행 중 사업 재확인 주기(철도·신도시 일정이 자주 밀림). 몇 달 써 보고 조정
GOV = re.compile(r"(^|\.)(go\.kr|korea\.kr|lh\.or\.kr|applyhome\.co\.kr)$")
_KR2 = {"co", "or", "go", "ne", "re", "ac", "pe"}


def outlet(url: str) -> str:
    """주소 → 언론사(등록 도메인). m.·mobile.·biz. 같은 앞부분은 같은 언론사로 본다."""
    h = urlparse(url or "").netloc.lower().split(":")[0]
    p = h.split(".")
    if len(p) >= 3 and p[-1] == "kr" and p[-2] in _KR2:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def grade(sources) -> str:
    hs = {outlet(u) for u in sources if u}
    if any(GOV.search(h) for h in hs):
        return "B"
    return "C" if len(hs) >= 2 else "D"


def stale(items, today: date) -> list[tuple[str, date]]:
    """(이름, 확인일) 중 STALE_DAYS 넘은 것, 오래된 순."""
    return sorted([(n, c) for n, c in items if c and (today - c).days > STALE_DAYS], key=lambda x: x[1])
