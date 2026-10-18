"""통계청 KOSIS Open API (통계자료 조회).

호출 (2026-10-12 실제 응답으로 확인, 키는 환경 변수 KOSIS_API_KEY):
  GET https://kosis.kr/openapi/Param/statisticsParameterData.do
      ?method=getList&apiKey=&format=json&jsonVD=Y&orgId=101&tblId=<표>&itmId=<항목>&objL1=<분류>
      &prdSe=M&startPrdDe=YYYYMM&endPrdDe=YYYYMM
  응답: [{"PRD_DE": "202608", "DT": "2.7", "ITM_NM": "실업률", "C1_NM": "계", ...}, ...]
        오류는 {"err": "30", "errMsg": "데이터가 존재하지 않습니다."} 같은 객체
  itmId·objL1 을 ALL 로 크게 요청하면 연결이 끊기는 일이 있었다 → 필요한 항목만 요청한다.

키는 출력·로그·예외 메시지에 싣지 않는다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from collector.sources.molit import ApiError, QuotaExceeded

URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


@dataclass(frozen=True)
class Series:
    tbl_id: str
    itm_id: str
    objs: tuple[str, ...]      # objL1, objL2, ... 분류 코드
    org_id: str = "101"
    year_to_date: bool = False  # 월별 누계(1월부터 쌓인 값) → 달별 값으로 바꾼다


_A, _B, _C, _D = "13102766969A", "13102766969B.0006", "13102766969C.0007", "13102766969D.0008"   # 착공: 구분, 아파트×3
_PA, _PB, _PC, _PD = "13102871090A", "13102871090B.0006", "13102871090C.0007", "13102871090D.0009"  # 인허가
SERIES = {
    # 계절조정 경제활동인구 총괄 > 계 > 실업률(%). 2000-01 부터 (G5, B4 ③)
    "unemployment_sa": Series("DT_1DA9001S", "T80", ("00",)),
    # F2 (📖 p.54~56) 국토교통부 주택유형별 주택건설 착공실적(월계) > 아파트, 호. 2011-01 부터
    "starts_sudo": Series("DT_MLTM_5387", "13103766969T1", (f"{_A}.0002", _B, _C, _D), "116"),
    "starts_seoul": Series("DT_MLTM_5387", "13103766969T1", (f"{_A}.0003", _B, _C, _D), "116"),
    # 주택유형별 주택건설 인허가실적(월별 누계) > 아파트, 호. 2007 부터
    "permits_sudo": Series("DT_MLTM_1948", "13103871090T1", (f"{_PA}.0002", _PB, _PC, _PD), "116", year_to_date=True),
    "permits_seoul": Series("DT_MLTM_1948", "13103871090T1", (f"{_PA}.0003", _PB, _PC, _PD), "116", year_to_date=True),
    # F3 (📖 p.155~160) 시·군·구별 미분양현황 > 시도 계, 호. 2000 부터
    "unsold_seoul": Series("DT_MLTM_2082", "13103871087T1", ("13102871087A.0002", "13102871087B.0001"), "116"),
    "unsold_incheon": Series("DT_MLTM_2082", "13103871087T1", ("13102871087A.0005", "13102871087B.0001"), "116"),
    "unsold_gyeonggi": Series("DT_MLTM_2082", "13103871087T1", ("13102871087A.0009", "13102871087B.0001"), "116"),
    # 공사완료후(준공 후) 미분양현황 > 시도 > 계·계·계, 호. 2007 부터
    "unsold_done_seoul": Series("DT_MLTM_5328", "13103871088T1", ("13102871088A.0002", "13102871088B.0002", "13102871088C.0001", "13102871088D.0001"), "116"),
    "unsold_done_incheon": Series("DT_MLTM_5328", "13103871088T1", ("13102871088A.0006", "13102871088B.0002", "13102871088C.0001", "13102871088D.0001"), "116"),
    "unsold_done_gyeonggi": Series("DT_MLTM_5328", "13103871088T1", ("13102871088A.0010", "13102871088B.0002", "13102871088C.0001", "13102871088D.0001"), "116"),
}


def _call(params: dict, retries: int = 5) -> list | dict:
    q = urllib.parse.urlencode({"method": "getList", "apiKey": os.environ["KOSIS_API_KEY"], "format": "json", "jsonVD": "Y", **params})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(URL + "?" + q, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise QuotaExceeded("HTTP 429") from None
            raise ApiError(f"HTTP {e.code}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise ApiError("connection failed") from None
            time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


def parse(j: list | dict) -> list[tuple[str, float]]:
    """응답 → [(YYYYMM, 값)] 오래된 것부터. 데이터 없음(err 30)은 빈 목록, 그 밖의 오류는 ApiError."""
    if isinstance(j, dict):
        if str(j.get("err")) == "30":
            return []
        raise ApiError(f"KOSIS err {j.get('err')} {j.get('errMsg')}")
    return sorted((r["PRD_DE"], float(r["DT"])) for r in j if r.get("DT") not in (None, "", "-"))


def from_year_to_date(pts: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """월별 누계 → 달별 값. 1월은 그대로, 이후 달은 전달 누계와의 차. 전달이 빠지면 그 달은 버린다."""
    d = dict(pts)
    out = []
    for p, v in pts:
        if p.endswith("01"):
            out.append((p, v))
        else:
            prev = f"{p[:4]}{int(p[4:]) - 1:02d}"
            if prev in d:
                out.append((p, v - d[prev]))
    return out


def fetch(name: str, start: str, end: str) -> list[tuple[str, float]]:
    s = SERIES[name]
    objs = {f"objL{i + 1}": o for i, o in enumerate(s.objs)}
    pts = parse(_call({"orgId": s.org_id, "tblId": s.tbl_id, "itmId": s.itm_id, **objs,
                       "prdSe": "M", "startPrdDe": start, "endPrdDe": end}))
    return from_year_to_date(pts) if s.year_to_date else pts


# F3 시군구별 미분양 (📖 원인 5가지 p.155~160). C1 = 시도, C2 = 시군구(경기는 시 단위, 인천은 2026-07 개편 뒤 구 이름).
# 2026-10-18 실제 응답으로 확인: 서울 25구, 인천 11곳, 경기 31시군
UNSOLD_SIDO = {"서울": ("13102871087A.0002", "13102871088A.0002"), "인천": ("13102871087A.0005", "13102871088A.0006"),
               "경기": ("13102871087A.0009", "13102871088A.0010")}


def fetch_unsold_sgg(start: str, end: str) -> list[dict]:
    """[{period, sido, name, unsold, unsold_done}] 시도 '계' 행은 뺀다. 준공 후 값이 없는 시군구는 None."""
    out: dict[tuple[str, str, str], dict] = {}
    for sido, (a_all, a_done) in UNSOLD_SIDO.items():
        for r in _rows(_call({"orgId": "116", "tblId": "DT_MLTM_2082", "itmId": "13103871087T1", "objL1": a_all, "objL2": "ALL",
                              "prdSe": "M", "startPrdDe": start, "endPrdDe": end})):
            if r["C2_NM"] != "계":
                out[(r["PRD_DE"], sido, r["C2_NM"])] = dict(period=r["PRD_DE"], sido=sido, name=r["C2_NM"], unsold=int(float(r["DT"])), unsold_done=None)
        for r in _rows(_call({"orgId": "116", "tblId": "DT_MLTM_5328", "itmId": "13103871088T1", "objL1": a_done, "objL2": "ALL",
                              "objL3": "13102871088C.0001", "objL4": "13102871088D.0001", "prdSe": "M", "startPrdDe": start, "endPrdDe": end})):
            k = (r["PRD_DE"], sido, r["C2_NM"])
            if r["C2_NM"] != "계" and k in out:
                out[k]["unsold_done"] = int(float(r["DT"]))
    return sorted(out.values(), key=lambda x: (x["period"], x["sido"], x["name"]))


def _rows(j: list | dict) -> list[dict]:
    if isinstance(j, dict):
        if str(j.get("err")) == "30":
            return []
        raise ApiError(f"KOSIS err {j.get('err')} {j.get('errMsg')}")
    return [r for r in j if r.get("DT") not in (None, "", "-")]


def sgg_codes(sido: str, name: str, regions: dict[str, str]) -> list[str]:
    """KOSIS 시군구 이름 → 우리 시군구 코드들. 경기 '수원시' → 수원시 4개 구. 못 찾으면 []."""
    pre = f"{sido} {name}"
    return sorted(c for c, n in regions.items() if n == pre or n.startswith(pre + " "))
