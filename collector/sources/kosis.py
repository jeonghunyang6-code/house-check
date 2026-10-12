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
    obj_l1: str
    org_id: str = "101"


SERIES = {
    # 계절조정 경제활동인구 총괄 > 계 > 실업률(%). 2000-01 부터 (G5, B4 ③)
    "unemployment_sa": Series("DT_1DA9001S", "T80", "00"),
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


def fetch(name: str, start: str, end: str) -> list[tuple[str, float]]:
    s = SERIES[name]
    return parse(_call({"orgId": s.org_id, "tblId": s.tbl_id, "itmId": s.itm_id, "objL1": s.obj_l1,
                        "prdSe": "M", "startPrdDe": start, "endPrdDe": end}))
