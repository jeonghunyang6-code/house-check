"""전국도시공원정보표준데이터 (공공데이터포털 15012890, 키 DATA_GO_KR_SERVICE_KEY, 활용 신청 필요). 입지 사실표 '공원' 줄(2026-11-11 사용자 요청).

설명용 사실만(점수화하지 않음, 관점 M3). 어린이공원·소공원은 단지마다 너무 많아 빼고, 근린공원 이상(근린·체육·역사·수변·문화 등)에서 가장 가까운 곳.
표준데이터 필드 이름(parkNm 공원명, parkSe 공원구분, latitude, longitude, parkAr 면적㎡, rdnmadr·lnmadr 주소)은 포털 안내 기준이며,
이 세션에서는 포털 접속이 막혀 실제 응답으로 확인하지 못함 → jobs/infra.py park 가 첫 행 필드를 찍고, 좌표를 하나도 못 읽으면 쓰지 않고 멈춘다.
"""

from __future__ import annotations

URL = "https://api.data.go.kr/openapi/tn_pubr_public_cty_park_info_api"
PAGE = 1000
NEAR_M = 2000                     # 🔧 이보다 먼 공원은 '없음'(설명용 표시 범위)
SMALL = ("어린이", "소공원", "묘지")  # 공원구분에 이 말이 있으면 뺀다
REGION = ("서울", "경기", "인천")


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def items(body: dict) -> tuple[int, list[dict]]:
    """표준데이터 API 응답 → (전체 건수, 행). items 가 목록이거나 {'item': …} 둘 다 받는다."""
    b = (body.get("response") or {}).get("body") or {}
    it = b.get("items")
    if isinstance(it, dict):
        it = it.get("item")
    if isinstance(it, dict):
        it = [it]
    return int(_num(b.get("totalCount")) or 0), list(it or [])


def normalize(r: dict) -> dict | None:
    lat, lng = _num(r.get("latitude")), _num(r.get("longitude"))
    if lat is None or lng is None or not (33 < lat < 39 and 124 < lng < 132):
        return None
    addr = (r.get("rdnmadr") or r.get("lnmadr") or "").strip()
    return {"name": (r.get("parkNm") or "").strip(), "kind": (r.get("parkSe") or "").strip(),
            "area": _num(r.get("parkAr")), "lat": lat, "lng": lng, "addr": addr}


def keep(p: dict) -> bool:
    """수도권 근린공원 이상. 주소가 없으면 좌표 범위(수도권 대략)로."""
    if not p["name"] or any(s in p["kind"] for s in SMALL):
        return False
    if p["addr"]:
        return p["addr"].startswith(REGION)
    return 36.9 < p["lat"] < 38.3 and 126.3 < p["lng"] < 127.9
