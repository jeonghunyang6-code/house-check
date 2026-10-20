"""직장까지 자차 시간: 네이버 클라우드 Maps Directions 5 (2026-10-21 사용자 결정, 찾기 탭 출퇴근 필터).

GET {URL}?start=경도,위도&goal=경도,위도&option=trafast, 헤더 x-ncp-apigw-api-key-id / x-ncp-apigw-api-key
(시크릿 NCP_MAPS_KEY_ID·NCP_MAPS_KEY = 네이버 클라우드 콘솔 Maps 'Application' 의 Client ID·Secret, Directions 5 사용 체크).
응답 route.trafast[0].summary.duration(밀리초)·distance(미터) — 공식 문서(api.ncloud-docs.com ai-naver-mapsdirections-driving) 기준, 실제 응답으로 아직 확인 못 함.
문서의 주소는 naveropenapi.apigw.ntruss.com. 2025년 새 Maps 콘솔 앱은 maps.apigw.ntruss.com 이라는 안내가 있어 둘 다 둔다(첫 응답으로 확인).
출발 시각 옵션이 없다 → 평일 출근 시간대에 돌린다. 401·403·429 는 멈춘다(우회 안 함).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

URLS = ("https://maps.apigw.ntruss.com/map-direction/v1/driving", "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving")
# 목적지: 입지톡(네이버 지오코딩) 2026-10-20. 키는 DB 에 들어가니 바꾸지 않는다
DESTS = {
    "skh_icheon": ("SK하이닉스 이천", 37.25298, 127.48069),
    "yongin_cluster": ("용인 반도체 클러스터", 37.16232, 127.33242),
}


class Stop(Exception):
    """키 오류·호출 한도 → 그날은 멈춘다."""


def parse(d: dict) -> tuple[float, float] | None:
    """응답 → (분, km). 경로 없음(code != 0)이면 None."""
    if d.get("code") != 0:
        return None
    r = (d.get("route") or {}).get("trafast") or []
    if not r:
        return None
    s = r[0].get("summary") or {}
    if s.get("duration") is None:
        return None
    return round(s["duration"] / 60000, 1), round((s.get("distance") or 0) / 1000, 1)


def call(lat: float, lng: float, dest: str, key_id: str, key: str, base: str, opener=urllib.request.urlopen) -> dict:
    _, dla, dlo = DESTS[dest]
    q = urllib.parse.urlencode({"start": f"{lng},{lat}", "goal": f"{dlo},{dla}", "option": "trafast"})
    req = urllib.request.Request(f"{base}?{q}", headers={"x-ncp-apigw-api-key-id": key_id, "x-ncp-apigw-api-key": key})
    try:
        with opener(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        if e.code in (401, 403, 429):
            raise Stop(f"HTTP {e.code} {body}") from None
        raise


def pick_base(lat: float, lng: float, key_id: str, key: str, opener=urllib.request.urlopen) -> str:
    """두 주소 중 이 키로 되는 것(첫 호출로 확인). 둘 다 401·403 이면 Stop."""
    last = None
    for base in URLS:
        try:
            call(lat, lng, next(iter(DESTS)), key_id, key, base, opener)
            return base
        except (Stop, urllib.error.URLError) as e:
            last = e
    raise Stop(f"두 주소 모두 실패: {last}")


def keys() -> tuple[str, str]:
    kid, k = os.environ.get("NCP_MAPS_KEY_ID", "").strip(), os.environ.get("NCP_MAPS_KEY", "").strip()
    if not kid or not k:
        raise Stop("NCP_MAPS_KEY_ID·NCP_MAPS_KEY 환경 변수가 없습니다")
    return kid, k


def pause(n: int, per_sec: float = 5.0) -> None:
    time.sleep(1 / per_sec)
