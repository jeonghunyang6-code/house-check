"""지지옥션 월간 경매동향 기사에서 지역별 아파트 낙찰가율을 뽑는다 (지표 G6 보조 소스).

기사 문장은 대체로 두 모양이다.
  ① "서울 아파트 낙찰가율은 94.7%로 집계됐다"            (지역 → 아파트 낙찰가율)
  ② "제주는 75.5%로 전월(82.5%)보다 7.0%p 떨어져"        (지역 → 값 → 전월값)
②는 앞뒤 문맥에 '낙찰가율'이 있을 때만 인정한다.

한계: 기사마다 문장 구조가 달라 놓치는 수치가 있을 수 있다. 그래서 같은 달 서로 다른 기사 2건 이상에서
같은 수치가 나올 때만 `confirm`이 확정한다. 확정되지 않은 값은 화면에 쓰지 않는다.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

REGIONS = ("전국|서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주")
_NUM = r"(\d{2,3}(?:\.\d{1,2})?)\s*%"

# ① 지역 + 아파트 낙찰가율 + 값
_P1 = re.compile(rf"({REGIONS})\s*(?:지역\s*)?아파트\s*낙찰가율(?:은|이|도|는)?\s*{_NUM}")
# ② 지역 + 은/는 + 값 + (전월 값)
_P2 = re.compile(rf"({REGIONS})(?:은|는)\s*{_NUM}\s*(?:로|으로)?\s*전월\(\s*{_NUM}\s*\)")


@dataclass(frozen=True)
class Candidate:
    region: str
    ratio_pct: float
    prev_pct: float | None
    sentence: str


def _sentences(text: str) -> list[str]:
    # 소수점의 마침표는 문장 끝이 아니므로 "숫자.숫자"는 보호한다
    guarded = re.sub(r"(?<=\d)\.(?=\d)", "\u0000", text)
    parts = re.split(r"(?<=[다요음임])\.\s*|\n+", guarded)
    return [p.replace("\u0000", ".").strip() for p in parts if p.strip()]


def extract(text: str) -> list[Candidate]:
    """기사 본문에서 (지역, 낙찰가율) 후보를 뽑는다. 같은 지역은 마지막 문맥 규칙 적용 전 중복 제거."""
    found: dict[str, Candidate] = {}
    sentences = _sentences(text)
    for i, s in enumerate(sentences):
        for m in _P1.finditer(s):
            region, value = m.group(1), float(m.group(2))
            found.setdefault(region, Candidate(region, value, _prev(s), s))
        # ②는 같은 문장 또는 바로 앞 문장에 '낙찰가율'이 있어야 한다
        context = " ".join(sentences[max(0, i - 1) : i + 1])
        if "낙찰가율" in context:
            for m in _P2.finditer(s):
                region = m.group(1)
                found.setdefault(region, Candidate(region, float(m.group(2)), float(m.group(3)), s))
    return list(found.values())


def _prev(sentence: str) -> float | None:
    m = re.search(rf"전월\(\s*{_NUM}\s*\)", sentence)
    return float(m.group(1)) if m else None


def confirm(articles: dict[str, list[Candidate]], min_sources: int = 2) -> dict[str, float]:
    """기사별 후보 → 지역별 확정값. 서로 다른 기사 `min_sources`건 이상에서 같은 값이 나온 경우만 인정."""
    votes: dict[tuple[str, float], set[str]] = defaultdict(set)
    for article_id, cands in articles.items():
        for c in cands:
            votes[(c.region, c.ratio_pct)].add(article_id)
    by_region: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for (region, value), srcs in votes.items():
        by_region[region].append((value, len(srcs)))
    confirmed: dict[str, float] = {}
    for region, vals in by_region.items():
        value, n = max(vals, key=lambda v: v[1])
        # 같은 지역에서 서로 다른 값이 같은 표를 얻으면 모호하므로 확정하지 않는다
        tied = [v for v, c in vals if c == n]
        if n >= min_sources and len(tied) == 1:
            confirmed[region] = value
    return confirmed
