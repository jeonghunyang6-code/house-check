"""건강보험심사평가원 병원정보서비스 getHospBasisList (공공데이터포털 키 DATA_GO_KR_SERVICE_KEY, 활용 신청 필요).

2026-10-15 실제 응답으로 필드 확인: yadmNm, clCd(01 상급종합·11 종합병원·31 의원 …), clCdNm, XPos(경도), YPos(위도).
"""

from __future__ import annotations

import math

from collector.infra import dist_m

URL = "https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
SIDO = {"110000": "서울", "220000": "인천", "310000": "경기"}   # 심평원 시도 코드
PAGE = 1000
BIG = {"01", "11"}            # 상급종합병원, 종합병원
CLINIC = {"31"}               # 의원
CLINIC_M = 1000               # 단지에서 이 직선거리 안의 의원 수


def items(body: dict) -> tuple[int, list[dict]]:
    b = body["response"]["body"]
    it = (b.get("items") or {}) if isinstance(b.get("items"), dict) else {}
    rows = it.get("item") or []
    if isinstance(rows, dict):                     # 한 건이면 목록이 아니라 객체로 온다
        rows = [rows]
    return int(b.get("totalCount") or 0), rows


def normalize(r: dict) -> dict | None:
    try:
        lng, lat = float(r.get("XPos")), float(r.get("YPos"))
    except (TypeError, ValueError):
        return None
    if not (33 < lat < 39 and 124 < lng < 132):
        return None
    return {"name": (r.get("yadmNm") or "").strip(), "kind": str(r.get("clCd") or "").strip(),
            "kind_nm": (r.get("clCdNm") or "").strip(), "lat": lat, "lng": lng}


class Grid:
    """약 1km 칸으로 나눠 가까운 점만 본다."""

    def __init__(self, pts: list[dict], cell: float = 0.01):
        self.cell, self.cells = cell, {}
        for p in pts:
            self.cells.setdefault((math.floor(p["lat"] / cell), math.floor(p["lng"] / cell)), []).append(p)

    def around(self, lat: float, lng: float, r: int):
        ci, cj = math.floor(lat / self.cell), math.floor(lng / self.cell)
        for i in range(ci - r, ci + r + 1):
            for j in range(cj - r, cj + r + 1):
                yield from self.cells.get((i, j), ())


def count_within(grid: Grid, lat: float, lng: float, m: float) -> int:
    r = math.ceil(m / (grid.cell * 88000)) + 1      # 경도 0.01도 ≈ 880m (북위 37도), 위도는 더 길다
    return sum(1 for p in grid.around(lat, lng, r) if dist_m(lat, lng, p["lat"], p["lng"]) <= m)
