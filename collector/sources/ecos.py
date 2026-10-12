"""한국은행 ECOS Open API (통계 조회).

호출 (2026-10-12 실제 응답으로 확인, 키는 환경 변수 ECOS_API_KEY):
  GET https://ecos.bok.or.kr/api/StatisticSearch/<키>/json/kr/<시작>/<끝>/<통계표>/M/<YYYYMM>/<YYYYMM>/<항목>
  응답: {"StatisticSearch": {"list_total_count": n, "row": [{"TIME": "202608", "DATA_VALUE": "4.66", ...}]}}
        데이터가 없으면 {"RESULT": {"CODE": "INFO-200", ...}}
  ecos.bok.kr 은 인증서가 *.bok.or.kr 용이라 HTTPS 가 실패한다 → ecos.bok.or.kr 을 쓴다.

키가 URL 경로에 들어가므로 URL·예외 메시지를 출력하지 않는다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from collector.sources.molit import ApiError, QuotaExceeded

BASE = "https://ecos.bok.or.kr/api/StatisticSearch"


@dataclass(frozen=True)
class Series:
    stat: str
    item: str
    cycle: str = "M"   # M 월간(YYYYMM) | A 연간(YYYY)


SERIES = {
    # 1.3.3.2.1 예금은행 대출금리(신규취급액 기준) > 주택담보대출, 연%. 2001-09 부터 (G3)
    "mortgage_rate": Series("121Y006", "BECBLA0302"),
    # 1.2.4.2.2 예금취급기관 가계대출(용도별, 월말 잔액), 십억원. 2003-10 부터 (G4)
    "household_loans": Series("151Y005", "1110000"),
    # 같은 표 > 주택관련대출-예금취급기관. 2007-12 부터 (G4 참고)
    "housing_loans": Series("151Y005", "11100A0"),
    # G1 유동성·소득·집값 (📖 p.50, 2005 = 100 으로 재기준화해 겹친다)
    "m2": Series("161Y005", "BBHS00"),                   # 1.1.3.1.1 M2 평잔, 계절조정, 십억원. 2003-10 부터
    "household_income": Series("200Y116", "1060130", "A"),  # 2.1.3.2.2 가계 및 비영리단체 처분가능소득(명목), 십억원. 연간
    "apt_kb_nat": Series("901Y062", "P63AC"),            # 4.4.1.1 KB 주택매매가격지수 > 아파트(전국). 1986-01 부터
    "apt_kb_seoul": Series("901Y062", "P63ACA"),         # 같은 표 > 아파트(서울)
}


def _call(path: str, retries: int = 5) -> dict:
    url = f"{BASE}/{os.environ['ECOS_API_KEY']}/json/kr/{path}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
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


def parse(j: dict) -> list[tuple[str, float]]:
    """응답 → [(YYYYMM, 값)] 오래된 것부터. 데이터 없음(INFO-200)은 빈 목록, 그 밖의 오류는 ApiError."""
    if "StatisticSearch" not in j:
        res = j.get("RESULT", {})
        if res.get("CODE") == "INFO-200":
            return []
        raise ApiError(f"ECOS {res.get('CODE')} {res.get('MESSAGE')}")
    return sorted((r["TIME"], float(r["DATA_VALUE"])) for r in j["StatisticSearch"]["row"] if r.get("DATA_VALUE") not in (None, ""))


def fetch(name: str, start: str, end: str) -> list[tuple[str, float]]:
    """start·end 는 YYYYMM. 연간 지표는 앞 4자리만 쓰고 (YYYY, 값)을 돌려준다."""
    s = SERIES[name]
    if s.cycle == "A":
        start, end = start[:4], end[:4]
    return parse(_call(f"1/10000/{s.stat}/{s.cycle}/{start}/{end}/{s.item}"))
