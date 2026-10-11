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
RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
# 이 환경(클라우드 세션)에서는 1000건 요청 시 터널이 끊겨 100 이 기본. Actions 에서는 HC_PAGE_SIZE=1000 을 시도한다(미검증).
PAGE_SIZE = int(os.environ.get("HC_PAGE_SIZE", "100"))


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


@dataclass(frozen=True)
class Rent:
    """전월세 1건. 2026-10-11 실제 응답(강남 2026-09, 1,119건 중 100건)으로 필드 확인.

    - deposit / monthlyRent : 만원, 쉼표 포함. monthlyRent '0' 이면 전세
    - contractType          : '신규' | '갱신' | '' (공백 14%)
    - useRRRight            : '사용' 이면 갱신요구권 사용, 아니면 공백
    - contractTerm          : '26.10~28.10' (계약기간, 공백 가능)
    - preDeposit / preMonthlyRent : 종전 계약 (갱신일 때)
    해제 필드는 없다.
    """

    apt_seq: str
    apt_name: str
    region_code: str
    contract_date: date
    area_m2: float
    floor: int | None
    deposit_10k: int
    monthly_rent_10k: int
    contract_type: str | None  # '신규' | '갱신' | None
    used_renewal_right: bool
    contract_term: str | None  # 원문
    term_start: date | None  # 계약기간 시작 월 1일
    term_end: date | None
    pre_deposit_10k: int | None
    pre_monthly_rent_10k: int | None
    is_cancelled: bool = False  # 스냅샷 비교 공용 (전월세는 해제 개념 없음)

    @property
    def deal_key(self) -> str:
        return (f"{self.apt_seq}|{self.contract_date.isoformat()}|{self.area_m2:g}|{self.floor}|"
                f"{self.deposit_10k}|{self.monthly_rent_10k}")


class ApiError(RuntimeError):
    pass


class QuotaExceeded(ApiError):
    """일일 호출 한도 초과(또는 HTTP 429). 재시도하지 않고 작업 전체를 멈춘다."""


def _t(item: ET.Element, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _yy_mm_dd(s: str) -> date | None:
    if not s:
        return None
    yy, mm, dd = s.split(".")
    return date(2000 + int(yy), int(mm), int(dd))


def _money(s: str) -> int | None:
    s = s.replace(",", "").strip()
    return int(s) if s else None


def _term(s: str) -> tuple[date | None, date | None]:
    """'26.10~28.10' → (2026-10-01, 2028-10-01). 형식이 다르면 (None, None)."""
    try:
        a, b = s.split("~")
        (ya, ma), (yb, mb) = a.split("."), b.split(".")
        return date(2000 + int(ya), int(ma), 1), date(2000 + int(yb), int(mb), 1)
    except ValueError:
        return None, None


def _item_to_rent(item: ET.Element) -> Rent:
    term = _t(item, "contractTerm")
    start, end = _term(term) if term else (None, None)
    ctype = _t(item, "contractType")
    return Rent(
        apt_seq=_t(item, "aptSeq"),
        apt_name=_t(item, "aptNm"),
        region_code=_t(item, "sggCd"),
        contract_date=date(int(_t(item, "dealYear")), int(_t(item, "dealMonth")), int(_t(item, "dealDay"))),
        area_m2=float(_t(item, "excluUseAr")),
        floor=int(_t(item, "floor")) if _t(item, "floor") else None,
        deposit_10k=_money(_t(item, "deposit")) or 0,
        monthly_rent_10k=_money(_t(item, "monthlyRent")) or 0,
        contract_type=ctype if ctype in ("신규", "갱신") else None,
        used_renewal_right=_t(item, "useRRRight") == "사용",
        contract_term=term or None,
        term_start=start,
        term_end=end,
        pre_deposit_10k=_money(_t(item, "preDeposit")),
        pre_monthly_rent_10k=_money(_t(item, "preMonthlyRent")),
    )


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


_QUOTA_MARKERS = ("LIMITED_NUMBER_OF_SERVICE_REQUESTS", "EXCEEDS")


def _parse_page(xml_text: str, conv):
    """한 페이지 XML → (목록, totalCount). 오류 응답이면 ApiError, 한도 초과면 QuotaExceeded."""
    root = ET.fromstring(xml_text)
    code = root.findtext("header/resultCode")
    if root.tag == "OpenAPI_ServiceResponse":  # 게이트웨이 오류 형식
        msg = root.findtext(".//returnAuthMsg") or "gateway error"
        reason = root.findtext(".//returnReasonCode") or ""
        if reason == "22" or any(m in msg for m in _QUOTA_MARKERS):
            raise QuotaExceeded(msg)
        raise ApiError(msg)
    if code is not None and code != "000":
        msg = f"resultCode={code} {root.findtext('header/resultMsg')}"
        if code == "22" or any(m in msg for m in _QUOTA_MARKERS):
            raise QuotaExceeded(msg)
        raise ApiError(msg)
    body = root.find("body")
    total = int(body.findtext("totalCount") or 0)
    return [conv(i) for i in body.findall("items/item")], total


def parse_trade_page(xml_text: str) -> tuple[list[Deal], int]:
    return _parse_page(xml_text, _item_to_deal)


def parse_rent_page(xml_text: str) -> tuple[list[Rent], int]:
    return _parse_page(xml_text, _item_to_rent)


def _get(url: str, params: dict[str, str | int], retries: int = 5) -> str:
    """429·403 은 재시도하지 않고 멈춘다. 터널 끊김 같은 연결 오류만 짧게 재시도한다."""
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(full, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise QuotaExceeded("HTTP 429") from None
            raise ApiError(f"HTTP {e.code}") from None  # URL(키 포함)을 예외에 싣지 않는다
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == retries - 1:
                raise ApiError("connection failed") from None
            time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


def _fetch_all(url: str, parse, lawd_cd: str, deal_ymd: str, service_key: str | None) -> list:
    key = service_key or os.environ["DATA_GO_KR_SERVICE_KEY"]
    out: list = []
    page = 1
    while True:
        xml_text = _get(
            url, {"serviceKey": key, "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd, "numOfRows": PAGE_SIZE, "pageNo": page}
        )
        rows, total = parse(xml_text)
        out.extend(rows)
        if len(out) >= total or not rows:
            return out
        page += 1


def fetch_trades(lawd_cd: str, deal_ymd: str, service_key: str | None = None) -> list[Deal]:
    """시군구 1곳·계약월 1개의 매매 전체 (해제 포함)."""
    return _fetch_all(TRADE_URL, parse_trade_page, lawd_cd, deal_ymd, service_key)


def fetch_rents(lawd_cd: str, deal_ymd: str, service_key: str | None = None) -> list[Rent]:
    """시군구 1곳·계약월 1개의 전월세 전체."""
    return _fetch_all(RENT_URL, parse_rent_page, lawd_cd, deal_ymd, service_key)
