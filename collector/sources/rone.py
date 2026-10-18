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


# (월) 매입자거주지별 아파트매매거래현황. 2006~, 시군구(경기는 시와 구 둘 다)별 매수자 거주지 5칸, 단위 동(호).
# 2026-10-18 실제 응답으로 확인: GRP_FULLNM '서울>송파구'·'경기>수원시>장안구', CLS_NM 아래 5개, ITM_ID 100001 = 건수(다른 ITM 은 면적)
BUYER_TABLE = "A_2024_00609"
BUYER_CLS = {"합계": "total", "관할시군구내": "same_sgg", "관할시도내": "same_sido", "관할시도외_서울": "seoul", "관할시도외_기타": "other"}


def parse_buyer(rows: list[dict]) -> list[dict]:
    """R-ONE 행 → 지역별 한 행 {period, grp_id, name, total, same_sgg, same_sido, seoul, other}. 수도권(서울·경기·인천)만."""
    by: dict[int, dict] = {}
    for r in rows:
        if int(r.get("ITM_ID") or 0) != 100001 or r.get("CLS_NM") not in BUYER_CLS or r.get("DTA_VAL") is None:
            continue
        name = r.get("GRP_FULLNM") or r.get("GRP_NM") or ""   # 전국 같은 최상위는 GRP_FULLNM 이 비어 있다
        if name.split(">")[0] not in CAPITAL_PREFIXES:
            continue
        g = by.setdefault(int(r["GRP_ID"]), {"period": r["WRTTIME_IDTFR_ID"], "grp_id": int(r["GRP_ID"]), "name": name})
        g[BUYER_CLS[r["CLS_NM"]]] = int(float(r["DTA_VAL"]))
    return [g for g in by.values() if "total" in g]


def fetch_buyer_month(ym: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        j = _call({"STATBL_ID": BUYER_TABLE, "DTACYCLE_CD": "MM", "WRTTIME_IDTFR_ID": ym, "pIndex": page, "pSize": 1000})
        if "SttsApiTblData" not in j:
            res = j.get("RESULT", {})
            if res.get("CODE") == "INFO-200":
                return []
            raise ApiError(f"{res.get('CODE')} {res.get('MESSAGE')}")
        blk = j["SttsApiTblData"]
        got = blk[1]["row"] if len(blk) > 1 else []
        rows += got
        if len(got) < 1000:
            return parse_buyer(rows)
        page += 1


def buyer_codes(name: str, regions: dict[str, str]) -> list[str]:
    """'경기>수원시>장안구' → ['41111'], '경기>수원시' → 수원시 4개 구, '서울' 같은 시도 합계·'인천>(구)중구' → []."""
    parts = name.split(">")
    if len(parts) < 2:
        return []
    pre = " ".join(parts)
    return sorted(c for c, n in regions.items() if n == pre or n.startswith(pre + " "))


# 월간 표 (jobs/region_stats.py, 0045). 2026-10-18 실제 응답으로 확인
JEONSE_RATIO_TABLE = "A_2024_00073"   # (월) 중위 매매가격 대비 전세가격_아파트, 2012~, 시군구(구)까지, % — D1 지역 평균
SENTIMENT_TABLE = "T235013129634707"   # 부동산시장 소비심리지수(국토연구원), 시도·수도권·전국 — G7
SIDO_KEYS = {"서울": "11", "인천": "28", "경기": "41", "수도권": "SUDO", "전국": "KR"}


def _rows_or_empty(j: dict) -> list[dict]:
    if "SttsApiTblData" not in j:
        res = j.get("RESULT", {})
        if res.get("CODE") == "INFO-200":
            return []
        raise ApiError(f"{res.get('CODE')} {res.get('MESSAGE')}")
    blk = j["SttsApiTblData"]
    return blk[1]["row"] if len(blk) > 1 else []


def fetch_monthly(statbl: str, ym: str | None = None, cls_id: int | None = None) -> list[dict]:
    """한 달의 모든 지역(ym) 또는 한 지역의 전체 시계열(cls_id). 행 그대로."""
    out, page = [], 1
    while True:
        q = {"STATBL_ID": statbl, "DTACYCLE_CD": "MM", "pIndex": page, "pSize": 1000}
        q.update({"WRTTIME_IDTFR_ID": ym} if ym else {"CLS_ID": cls_id})
        got = _rows_or_empty(_call(q))
        out += got
        if len(got) < 1000:
            return out
        page += 1


def region_key(full_name: str, sgg: dict[str, str]) -> str | None:
    """'수도권>서울'·'서울' → '11', '수도권>소계'·'수도권' → 'SUDO', '전국>소계' → 'KR', 시군구 경로 → 우리 코드(sgg = map_regions 결과)."""
    parts = [p for p in full_name.split(">") if p != "소계"]
    if len(parts) == 1 and parts[0] in SIDO_KEYS:
        return SIDO_KEYS[parts[0]]
    if len(parts) == 2 and parts[0] == "수도권" and parts[1] in SIDO_KEYS:
        return SIDO_KEYS[parts[1]]
    return sgg.get(full_name)
