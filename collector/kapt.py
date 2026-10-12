"""K-apt(공동주택관리정보시스템) 단지 목록·기본 정보와 실거래 단지의 연결.

호출 (2026-10-12 실제 응답으로 확인, 공공데이터포털 키 DATA_GO_KR_SERVICE_KEY):
- 단지 목록  GET apis.data.go.kr/1613000/AptListService4/getSigunguAptList4?sigunguCode=11680
             → items[]: kaptCode, kaptName, bjdCode(10자리), as1~as3
- 기본 정보  GET apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusBassInfoV5?kaptCode=
             → item: kaptdaCnt(세대수), kaptUsedate(YYYYMMDD), kaptAddr(지번 주소), doroJuso, kaptDongCnt,
               kaptTopFloor, kaptBcompany, codeHeatNm, codeSaleNm, kaptMparea60/85/135/136

실거래 aptSeq 와 kaptCode 사이에는 공통 키가 없다. 실거래의 법정동(sggCd+umdCd)·지번·도로명으로 맞춘다:
  1) 같은 법정동 + 같은 지번   2) 같은 도로명 주소   3) 같은 법정동 + 이름이 서로 포함
후보가 여럿이면 이름으로 좁히고, 그래도 여럿이면 연결하지 않는다(틀린 연결보다 빈칸이 낫다).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date

from collector.sources.molit import ApiError, QuotaExceeded, conn_failed, note_ok

LIST_URL = "https://apis.data.go.kr/1613000/AptListService4/getSigunguAptList4"
INFO_URL = "https://apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusBassInfoV5"


def _get_json(url: str, params: dict, retries: int = 5) -> dict:
    key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    full = url + "?" + urllib.parse.urlencode({"serviceKey": key, **params})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(full, timeout=40) as r:
                body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise QuotaExceeded("HTTP 429") from None
            raise ApiError(f"HTTP {e.code}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == retries - 1:
                raise conn_failed() from None
            time.sleep(2 * 2**attempt)
            continue
        note_ok()
        if body.lstrip().startswith("<"):  # 게이트웨이 오류는 XML 로 온다
            if "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in body:
                raise QuotaExceeded("daily quota")
            raise ApiError(re.sub(r"\s+", " ", body)[:200])
        j = json.loads(body)
        code = j.get("response", {}).get("header", {}).get("resultCode")
        if code not in ("00", "000", None):
            msg = j["response"]["header"].get("resultMsg", "")
            if code == "22":
                raise QuotaExceeded(msg)
            raise ApiError(f"resultCode={code} {msg}")
        return j
    raise AssertionError("unreachable")


def fetch_list(sigungu_code: str) -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        b = _get_json(LIST_URL, {"sigunguCode": sigungu_code, "numOfRows": 500, "pageNo": page})["response"]["body"]
        items = b.get("items") or []
        out += items
        if len(out) >= int(b.get("totalCount") or 0) or not items:
            return out
        page += 1


def fetch_info(kapt_code: str) -> dict | None:
    return _get_json(INFO_URL, {"kaptCode": kapt_code})["response"]["body"].get("item")


def _int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def info_row(item: dict) -> dict:
    """기본 정보 응답 → kapt_complexes 열."""
    ud = (item.get("kaptUsedate") or "").strip()
    return {
        "addr": (item.get("kaptAddr") or "").strip() or None,
        "road_addr": (item.get("doroJuso") or "").strip() or None,
        "households": _int(item.get("kaptdaCnt")),
        "use_date": date(int(ud[:4]), int(ud[4:6]), int(ud[6:8])) if re.fullmatch(r"\d{8}", ud) and ud[4:] != "0000" else None,
        "dong_cnt": _int(item.get("kaptDongCnt")),
        "top_floor": _int(item.get("kaptTopFloor")),
        "builder": (item.get("kaptBcompany") or "").strip() or None,
        "heat_type": (item.get("codeHeatNm") or "").strip() or None,
        "sale_type": (item.get("codeSaleNm") or "").strip() or None,
        "hh_lt60": _int(item.get("kaptMparea60")),
        "hh_60_85": _int(item.get("kaptMparea85")),
        "hh_85_135": _int(item.get("kaptMparea135")),
        "hh_gt135": _int(item.get("kaptMparea136")),
    }


# ---------- 연결 (순수 함수) ----------

def norm_jibun(s: str | None) -> str:
    """'0316', '316-0', '316번지' → '316'; '12-03' → '12-3'. 산 지번은 '산12'."""
    if not s:
        return ""
    s = s.strip().replace("번지", "")
    m = re.fullmatch(r"(산)?\s*0*(\d+)(?:-0*(\d+))?", s)
    if not m:
        return ""
    return (m.group(1) or "") + m.group(2) + (f"-{m.group(3)}" if m.group(3) and m.group(3) != "0" else "")


def jibun_from_addr(addr: str | None) -> str:
    """K-apt 지번 주소 '서울특별시 강남구 개포동 189 개포자이프레지던스' → '189'."""
    if not addr:
        return ""
    m = re.search(r"\S+(?:동|가|리)\s+(산?\s*\d+(?:-\d+)?)(?:번지)?(?=\s|$)", addr)
    return norm_jibun(m.group(1)) if m else ""


def road_from_addr(addr: str | None) -> str:
    """'서울특별시 강남구 삼성로 14' → '삼성로 14' (도로명 + 건물번호)."""
    if not addr:
        return ""
    m = re.search(r"(\S+(?:로|길))\s+(\d+(?:-\d+)?)", addr)
    if not m:
        return ""
    num = m.group(2)
    main, _, sub = num.partition("-")
    return f"{m.group(1)} {int(main)}" + (f"-{int(sub)}" if sub and int(sub) else "")


_DROP = re.compile(r"\(.*?\)|아파트|apt|[^0-9a-z가-힣]")


def norm_name(s: str | None) -> str:
    return _DROP.sub("", (s or "").lower())


def _names_match(a: str, b: str) -> bool:
    a, b = norm_name(a), norm_name(b)
    return bool(a and b) and (a in b or b in a)


@dataclass(frozen=True)
class Match:
    kapt_code: str
    method: str  # 'jibun' | 'road' | 'name'


def match_complexes(complexes: list[dict], kapts: list[dict]) -> dict[str, Match]:
    """complexes: apt_seq, apt_name, bjd_code, jibun, road_addr
    kapts: kapt_code, kapt_name, bjd_code, addr, road_addr
    → apt_seq → Match. 애매하면 결과에 넣지 않는다."""
    by_jibun: dict[tuple[str, str], list[dict]] = {}
    by_road: dict[str, list[dict]] = {}
    by_bjd: dict[str, list[dict]] = {}
    for k in kapts:
        j = jibun_from_addr(k.get("addr"))
        if k.get("bjd_code") and j:
            by_jibun.setdefault((k["bjd_code"], j), []).append(k)
        r = road_from_addr(k.get("road_addr"))
        if r:
            by_road.setdefault(r, []).append(k)
        if k.get("bjd_code"):
            by_bjd.setdefault(k["bjd_code"], []).append(k)

    def pick(cands: list[dict], name: str) -> dict | None:
        if len(cands) == 1:
            return cands[0]
        named = [k for k in cands if _names_match(name, k["kapt_name"])]
        return named[0] if len(named) == 1 else None

    out: dict[str, Match] = {}
    for c in complexes:
        name = c["apt_name"]
        j = norm_jibun(c.get("jibun"))
        k = pick(by_jibun.get((c.get("bjd_code") or "", j), []), name) if j else None
        if k:
            out[c["apt_seq"]] = Match(k["kapt_code"], "jibun")
            continue
        r = c.get("road_addr") or ""
        k = pick(by_road.get(r, []), name) if r else None
        if k:
            out[c["apt_seq"]] = Match(k["kapt_code"], "road")
            continue
        named = [k for k in by_bjd.get(c.get("bjd_code") or "", []) if _names_match(name, k["kapt_name"])]
        if len(named) == 1:
            out[c["apt_seq"]] = Match(named[0]["kapt_code"], "name")
    return out
