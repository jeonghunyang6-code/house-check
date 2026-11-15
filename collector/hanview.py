"""한강뷰 손 관리(입지 사실표 '한강', 2026-11-15 사용자 요청 B안). 지도 추정(collector/hanbank.py)보다 우선.

관심 단지만. 기사·분양 자료 2곳 이상(collector/provenance.py 등급 B·C) 또는 사용자가 직접 확인한 것(임장·매물 사진, '사용자 확인 날짜')만 넣는다.
한강뷰는 동·층·향마다 달라서 단지 하나에 '전 세대' / '일부 동' / '없음' 으로만 적는다(커뮤니티 통설: 같은 단지 안 풀 한강뷰는 비한강뷰보다 약 20% 비쌈 —
작가 출처가 아니라 판정 기준으로 쓰지 않음, docs/insights/viewpoints.md 밖 참고).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class HanView:
    kind: str                    # 전 세대 / 일부 동 / 없음
    note: str                    # 어느 동·층·향인지
    sources: tuple[str, ...]     # 주소, 또는 '사용자 확인'
    checked: date


# 2026-11-15: 관심 단지 중 한강 가까운 곳은 선사현대뿐인데, 동별 조망을 적은 기사·자료를 2곳 찾지 못해 비워 둠(지도 추정만 보임)
HANVIEW: dict[str, HanView] = {}
