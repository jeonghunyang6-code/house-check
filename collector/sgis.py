"""통계청 SGIS 오픈 API: 주소 → 좌표, 행정동 경계 (2026-10-14 GitHub 러너에서 실제 응답으로 확인).

키: SGIS_CONSUMER_KEY, SGIS_CONSUMER_SECRET (출력 금지). 이 클라우드 세션은 sgisapi.kostat.go.kr 접속이 막혀 있어 Actions 에서 돈다.
- 인증    GET /OpenAPI3/auth/authentication.json?consumer_key=&consumer_secret= → result.accessToken
- 좌표    GET /OpenAPI3/addr/geocodewgs84.json?accessToken=&address=&resultcount=1
          → result.resultdata[0]: x(경도), y(위도), adm_cd(SGIS 행정동 8자리), adm_nm, leg_cd(법정동 10자리, 예 1171010700), leg_nm
- 경계    GET /OpenAPI3/boundary/hadmarea.geojson?accessToken=&year=&adm_cd=<SGIS 시군구 5자리>&low_search=1
          → features[]: properties.adm_cd·adm_nm, geometry Polygon/MultiPolygon (UTM-K, EPSG:5179)
- 단계    GET /OpenAPI3/addr/stage.json?accessToken=&cd= → 하위 행정구역 목록 (SGIS 코드: 서울 11, 인천 23, 경기 31)
SGIS 시군구 코드(송파 11240)는 법정동 코드(송파 11710)와 다르다. 응답의 leg_cd 로 우리 법정동과 맞춘다.
"""

from __future__ import annotations

import re
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://sgisapi.kostat.go.kr/OpenAPI3"


class SgisError(Exception):
    pass


class Sgis:
    def __init__(self, key: str | None = None, secret: str | None = None, sleep=time.sleep):
        self.key = key or os.environ["SGIS_CONSUMER_KEY"]
        self.secret = secret or os.environ["SGIS_CONSUMER_SECRET"]
        self.token: str | None = None
        self.sleep = sleep

    def _raw(self, path: str, params: dict) -> dict:
        url = BASE + path + "?" + urllib.parse.urlencode(params)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=40) as r:
                    return json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError) as e:
                if attempt == 3:
                    raise SgisError(type(e).__name__) from None   # 메시지에 URL(토큰) 이 들어갈 수 있어 이름만
                self.sleep(2 * 2 ** attempt)
        raise AssertionError

    def _auth(self) -> None:
        j = self._raw("/auth/authentication.json", {"consumer_key": self.key, "consumer_secret": self.secret})
        tok = (j.get("result") or {}).get("accessToken")
        if not tok:
            raise SgisError(f"auth errCd={j.get('errCd')} {j.get('errMsg')}")
        self.token = tok

    def get(self, path: str, **params) -> dict:
        for _ in range(2):
            if not self.token:
                self._auth()
            j = self._raw(path, {"accessToken": self.token, **params})
            if path.endswith(".geojson") and "features" in j:
                return j
            code = j.get("errCd")
            if code in (0, "0"):
                return j
            if code in (-401, "-401"):          # 토큰 만료 → 다시 인증
                self.token = None
                continue
            if code in (-100, "-100"):          # 검색 결과 없음
                return {"result": None}
            raise SgisError(f"errCd={code} {j.get('errMsg')}")
        raise SgisError("auth retry failed")

    def geocode(self, address: str) -> dict | None:
        r = (self.get("/addr/geocodewgs84.json", address=address, resultcount=1).get("result") or {})
        rows = r.get("resultdata") or []
        return rows[0] if rows else None

    def stage(self, cd: str | None = None) -> list[dict]:
        return self.get("/addr/stage.json", **({"cd": cd} if cd else {})).get("result") or []

    def hadm_boundary(self, sgg_cd: str, year: str) -> list[dict]:
        return self.get("/boundary/hadmarea.geojson", year=year, adm_cd=sgg_cd, low_search="1").get("features") or []


SIDO_FULL = {"서울": "서울특별시", "인천": "인천광역시", "경기": "경기도"}


def address_candidates(region_name: str, umd: str | None, jibun: str | None, road: str | None, kapt_road: str | None) -> list[tuple[str, str]]:
    """(방식, 주소) 후보. region_name 예: '서울 송파구', '경기 화성시 동탄구'(2026 개편 — SGIS 가 새 구를 모를 수 있어 시까지만도 시도)."""
    parts = region_name.split()
    sido = SIDO_FULL.get(parts[0], parts[0])
    sgg_full = " ".join(parts[1:])
    sgg_city = parts[1] if len(parts) > 2 else sgg_full
    out = []
    ok_jibun = bool(jibun) and re.fullmatch(r"산?\d+(-\d+)?", jibun.strip()) is not None   # '가-' '지구BL'(지번 받기 전 블록) 같은 값은 SGIS 서버 오류(2026-10-26)
    for sgg in dict.fromkeys([sgg_full, sgg_city]):
        if umd and ok_jibun:
            out.append(("jibun", f"{sido} {sgg} {umd} {jibun}"))
        if road:
            out.append(("road", f"{sido} {sgg} {road}"))
    if kapt_road:
        out.append(("kapt_road", kapt_road))
    return list(dict.fromkeys(out))


def accept(hit: dict | None, bjd_code: str | None, umd: str | None, region_name: str = "") -> bool:
    """좌표가 우리 법정동과 맞는지: 법정동 코드가 같거나, (시군구 개편으로 코드가 달라진 곳) 동 이름이 같고 시군구 이름도 겹칠 때.
    이름만 보면 서울 양천구·마포구 신정동처럼 같은 이름의 다른 동을 받아들일 수 있다."""
    if not hit:
        return False
    leg_cd, leg_nm, sgg_nm = str(hit.get("leg_cd") or ""), str(hit.get("leg_nm") or ""), str(hit.get("sgg_nm") or "")
    if bjd_code and leg_cd == bjd_code:
        return True
    ours = region_name.split()[1:]
    # 읍·면 아래 리: 우리 쪽은 '우정읍 조암리', SGIS 는 읍·면 이름('우정읍')만 준다(2026-10-27 Actions 로그로 확인 — 화성 만세·효행구 138곳, 김포 고촌읍 등이 이래서 못 찾음).
    # 좌표는 주소 자체의 점이라 읍·면까지 맞으면 받아들인다
    same_umd = bool(umd) and (leg_nm == umd or (" " in umd and leg_nm in (umd.split()[0], umd.split()[-1])))
    return same_umd and bool(sgg_nm) and any(t in sgg_nm or sgg_nm in t for t in ours)
