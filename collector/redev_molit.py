"""H5 정비사업 단계 (경기) 자동 갱신: 국토교통부 '전국 도시정비사업 통합 데이터'(공공데이터 15160169, CSV, 연 1회 갱신).

2026-10-26 사용자 결정: 경기데이터드림 파일을 손으로 넣는 대신 이 자료로 자동(파일 열: 시도·시군구·구역명칭·현 사업추진단계·사업유형·
사업시행자·공급 예정 세대수). 지번이 없어 우리 경기 구역(redev_zone src='gg', 0065)과는 같은 시 + 구역 이름으로 맞춘다.
준공·예정구역은 이 자료에 없다. 1년에 한 번 갱신이라 늦을 수 있어, 우리 단계보다 **앞선 단계일 때만** 올린다(되돌리지 않음).
"""

from __future__ import annotations

import difflib
import re

# 국토부 단계 → (우리 단계, 번호). 사업시행자지정(공공 시행)은 조합설립에 해당하는 단계로 본다
STAGE = {"정비구역지정": ("구역지정", 1), "추진위구성": ("추진위", 2), "조합설립인가": ("조합설립", 3), "사업시행자지정": ("조합설립", 3),
         "사업시행인가": ("사업시행", 5), "관리처분인가": ("관리처분", 6), "착공": ("착공", 7)}


def stage_of(s: str) -> tuple[str, int] | None:
    return STAGE.get(re.sub(r"^\d+\)", "", (s or "").strip()))


def city(s: str) -> str:
    """'수원영통구' '수원시' '안양만안구' → '수원' '안양'. 시 이름은 모두 두 글자(경기)."""
    return re.sub(r"\s", "", s or "")[:2]


def norm(s: str) -> str:
    s = re.sub(r"[\s.·\-_,]", "", (s or "").replace("（", "(").replace("）", ")"))
    return re.sub(r"(재개발|재건축|정비|주택|구역|지구|사업|아파트)", "", s)


def parts(s: str) -> tuple[str, str]:
    """(괄호 밖, 괄호 안) 정규화. '영통3구역(원천주공)' → ('영통3', '원천주공')."""
    m = re.match(r"^(.*?)\((.*)\)\s*$", s or "")
    return (norm(m.group(1)), norm(m.group(2))) if m else (norm(s), "")


def _nums(s: str) -> list[str]:
    return re.findall(r"\d+", s)


def match(row: dict, zones: list[dict]) -> dict | None:
    """같은 시의 우리 구역 중 하나. ① 이름(정규화) 같음 ② 괄호 밖 또는 괄호 안이 같음 ③ 유사도 🔧0.85+·숫자 같음. 두 곳 이상이면 안 붙임."""
    c = city(row["시군구"])
    pool = [z for z in zones if city(z["district"]) == c]
    full, (out, inn) = norm(row["구역명칭"]), parts(row["구역명칭"])
    for test in (lambda z: norm(z["zone_nm"]) == full,
                 lambda z: (lambda o, i: (out and o == out) or (inn and (i == inn or o == inn)) or (o and o == inn))(*parts(z["zone_nm"]))):
        hit = [z for z in pool if test(z)]
        if len(hit) == 1:
            return hit[0]
        if len(hit) > 1:
            return None
    best = [(difflib.SequenceMatcher(None, full, norm(z["zone_nm"])).ratio(), z) for z in pool if _nums(full) == _nums(norm(z["zone_nm"]))]
    best = sorted((b for b in best if b[0] >= 0.85), key=lambda b: -b[0])
    return best[0][1] if len(best) == 1 or (len(best) > 1 and best[0][0] > best[1][0]) else None
