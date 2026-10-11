"""국토교통부 아파트 매매 실거래가 상세 자료 (공공데이터포털).

호출: GET https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev
      serviceKey, LAWD_CD(시군구 5자리), DEAL_YMD(계약월 YYYYMM), numOfRows, pageNo
응답 필드는 2026-10-11 실제 응답(서울 강남구 2026-08, 98건)으로 확인했다.
  - aptSeq        단지일련번호 (예: 11680-279). 법정동코드 5자리-일련번호
  - dealAmount    "312,000" (만원, 쉼표 포함)
  - cdealType     'O' 이면 계약 해제, 아니면 공백. cdealDay 는 해제 사유 발생일 "YY.MM.DD"
  - dealingGbn    '중개거래' | '직거래'
  - rgstDate      등기일 "YY.MM.DD" (신고일이 아니다. 등기 전이면 공백). 등록일(first_seen_date) 대용으로 쓰지 않는다
거래 고유 ID가 없어 deal_key 를 직접 만든다 (docs/ARCHITECTURE.md 4.1).

한계: 1페이지 numOfRows=1000 호출은 이 환경의 프록시에서 터널이 끊겼다. 100건씩 받는다.
서비스키는 환경 변수 DATA_GO_KR_SERVICE_KEY 에서만 읽고 출력·로그에 남기지 않는다.
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
PAGE_SIZE = 100


@dataclass(frozen=True)
class Deal:
    apt_seq: str
    apt_name: str
    region_code: str  # sggCd
    umd_name: str
    build_year: int | None
    contract_date: date
    area_m2: float
    floor: int
    price_10k: int
    deal_type: str  # '중개' | '직거래'
    is_cancelled: bool
    cancel_date: date | None
    rgst_date: date | None

    @property
    def area_group(self) -> int:
        return int(self.area_m2)  # 84.91 → 84 (docs 4.3)

    @property
    def deal_key(self) -> str:
        return f"{self.apt_seq}|{self.contract_date.isoformat()}|{self.area_m2:g}|{self.floor}|{self.price_10k}"


class ApiError(RuntimeError):
    pass


def _t(item: ET.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _yy_mm_dd(s: str) -> date | None:
    if not s:
        return None
    yy, mm, dd = s.split(".")
    return date(2000 + int(yy), int(mm), int(dd))


def _item_to_deal(item: ET.Element) -> Deal:
    cancelled = _t(item, "cdealType") == "O"
    return Deal(
        apt_seq=_t(item, "aptSeq"),
        apt_name=_t(item, "aptNm"),
        region_code=_t(item, "sggCd"),
        umd_name=_t(item, "umdNm"),
        build_year=int(_t(item, "buildYear")) if _t(item, "buildYear") else None,
        contract_date=date(int(_t(item, "dealYear")), int(_t(item, "dealMonth")), int(_t(item, "dealDay"))),
        area_m2=float(_t(item, "excluUseAr")),
        floor=int(_t(item, "floor")),
        price_10k=int(_t(item, "dealAmount").replace(",", "")),
        deal_type="직거래" if _t(item, "dealingGbn") == "직거래" else "중개",
        is_cancelled=cancelled,
        cancel_date=_yy_mm_dd(_t(item, "cdealDay")) if cancelled else None,
        rgst_date=_yy_mm_dd(_t(item, "rgstDate")),
    )


def parse_trade_page(xml_text: str) -> tuple[list[Deal], int]:
    """한 페이지 XML → (거래 목록, totalCount). 오류 응답이면 ApiError."""
    root = ET.fromstring(xml_text)
    code = root.findtext("header/resultCode")
    if code is not None and code != "000":
        raise ApiError(f"resultCode={code} {root.findtext('header/resultMsg')}")
    if root.tag == "OpenAPI_ServiceResponse":  # 게이트웨이 오류 형식
        raise ApiError(root.findtext(".//returnAuthMsg") or "gateway error")
    body = root.find("body")
    total = int(body.findtext("totalCount") or 0)
    return [_item_to_deal(i) for i in body.findall("items/item")], total


def _get(url: str, params: dict[str, str | int], retries: int = 5) -> str:
    """429·403 은 재시도하지 않고 멈춘다. 터널 끊김 같은 연결 오류만 짧게 재시도한다."""
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(full, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise ApiError(f"HTTP {e.code}") from None  # URL(키 포함)을 예외에 싣지 않는다
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == retries - 1:
                raise ApiError("connection failed") from None
            time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


def fetch_trades(lawd_cd: str, deal_ymd: str, service_key: str | None = None) -> list[Deal]:
    """시군구 1곳·계약월 1개의 거래 전체 (해제 포함)."""
    key = service_key or os.environ["DATA_GO_KR_SERVICE_KEY"]
    out: list[Deal] = []
    page = 1
    while True:
        xml_text = _get(
            TRADE_URL,
            {"serviceKey": key, "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd, "numOfRows": PAGE_SIZE, "pageNo": page},
        )
        deals, total = parse_trade_page(xml_text)
        out.extend(deals)
        if len(out) >= total or not deals:
            return out
        page += 1
