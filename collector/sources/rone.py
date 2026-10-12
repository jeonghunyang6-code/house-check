"""한국부동산원 R-ONE 주간 아파트 가격동향 Open API.

호출 (2026-10-12 실제 응답으로 확인, 키는 환경 변수 RONE_API_KEY):
  GET https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do
      ?KEY=&Type=json&STATBL_ID=<표>&DTACYCLE_CD=WK&WRTTIME_IDTFR_ID=<YYYYWW> | &CLS_ID=<지역>&pIndex=1&pSize=1000
  응답: {"SttsApiTblData": [{"head": [{"list_total_count": n}, {"RESULT": {...}}]}, {"row": [...]}]}
        데이터가 없으면 {"RESULT": {"CODE": "INFO-200", ...}} (예: 2025-10-06 주는 추석으로 발표 없음)
  row: CLS_ID, CLS_NM, CLS_FULLNM('경기>경부2권>수원시>영통구'), ITM_ID, DTA_VAL, WRTTIME_IDTFR_ID, WRTTIME_DESC('2026-10-05')

주차 번호는 ISO 주차와 같다(202641 = 2026-10-05 월요일, 202540 = 2025-09-29).
검증: 2026-10-05 주 서울 +0.12%, 수도권 +0.14%, 강남구 -0.34%, 연속 상승 서울 88주·수도권 84주가 외부 화면과 일치.
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
from datetime import date, timedelta

from collector.sources.molit import ApiError, QuotaExceeded

URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
TABLES = {  # stat → STATBL_ID (표 목록 SttsApiTbl.do 에서 확인)
    "sale": "T244183132827305",           # (주) 매매가격지수
    "jeonse": "T247713133046872",         # (주) 전세가격지수
    "sale_supply": "T248163133074619",    # (주) 매매수급동향 (권역 단위)
    "jeonse_supply": "T245423133086632",  # (주) 전세수급동향
}
CAPITAL_PREFIXES = ("서울", "경기", "인천")


@dataclass(frozen=True)
class Point:
    cls_id: int
    full_name: str
    name: str
    week_id: str
    week_date: date
    value: float


def _call(params: dict, retries: int = 6) -> dict:
    q = urllib.parse.urlencode({"KEY": os.environ["RONE_API_KEY"], "Type": "json", **params})
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


def parse(j: dict) -> list[Point]:
    """응답 → Point 목록. 데이터 없음(INFO-200)은 빈 목록, 그 밖의 오류는 ApiError."""
    if "SttsApiTblData" not in j:
        res = j.get("RESULT", {})
        if res.get("CODE") == "INFO-200":
            return []
        raise ApiError(f"{res.get('CODE')} {res.get('MESSAGE')}")
    blk = j["SttsApiTblData"]
    rows = blk[1]["row"] if len(blk) > 1 else []
    return [
        Point(int(r["CLS_ID"]), r["CLS_FULLNM"], r["CLS_NM"], r["WRTTIME_IDTFR_ID"],
              date.fromisoformat(r["WRTTIME_DESC"]), float(r["DTA_VAL"]))
        for r in rows if r.get("DTA_VAL") is not None
    ]


def fetch_week(stat: str, week_id: str) -> list[Point]:
    return parse(_call({"STATBL_ID": TABLES[stat], "DTACYCLE_CD": "WK", "WRTTIME_IDTFR_ID": week_id, "pIndex": 1, "pSize": 1000}))


def fetch_series(stat: str, cls_id: int) -> list[Point]:
    """한 지역의 전체 주간 시계열 (2012년 19주~, 약 750주)."""
    out: list[Point] = []
    page = 1
    while True:
        pts = parse(_call({"STATBL_ID": TABLES[stat], "DTACYCLE_CD": "WK", "CLS_ID": cls_id, "pIndex": page, "pSize": 1000}))
        out += pts
        if len(pts) < 1000:
            return out
        page += 1


def keep(stat: str, p: Point) -> bool:
    """저장 범위: 지수는 서울·경기·인천과 상위 집계(이름에 '>' 없음), 수급동향은 전부."""
    if stat.endswith("supply"):
        return True
    return p.full_name.split(">")[0] in CAPITAL_PREFIXES or ">" not in p.full_name


def week_id(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}{w:02d}"


def weeks_between(start: date, end: date) -> list[str]:
    """start 주부터 end 주까지 ISO 주차 번호 (월요일 기준)."""
    d = start - timedelta(days=start.weekday())
    out = []
    while d <= end:
        out.append(week_id(d))
        d += timedelta(days=7)
    return out


def map_regions(full_names: list[str], regions: dict[str, str]) -> dict[str, str]:
    """R-ONE 지역 경로 → 우리 시군구 코드 (collector/regions.py 의 '경기 수원시 영통구' 형식).
    경로 끝이 시군구 이름과 정확히 같고 후보가 하나일 때만 연결한다. 시 집계('경기>경부2권>수원시')는 연결하지 않는다.
    2026-10-05 주 기준 수도권 83개 중 78개 연결(강화·옹진·연천·가평·양평은 주간 조사 대상 아님)."""
    out: dict[str, str] = {}
    for code, name in regions.items():
        sido, rest = name.split(" ", 1)
        cands = [f for f in full_names if f.split(">")[0] == sido and f.endswith(">" + rest.replace(" ", ">"))]
        if len(cands) == 1:
            out[cands[0]] = code
    return out
