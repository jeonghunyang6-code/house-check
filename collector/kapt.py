"""K-apt(공동주택관리정보시스템) 단지 목록·기본 정보와 실거래 단지의 연결.

호출 (2026-10-12 실제 응답으로 확인, 공공데이터포털 키 DATA_GO_KR_SERVICE_KEY):
- 단지 목록  GET apis.data.go.kr/1613000/AptListService4/getSigunguAptList4?sigunguCode=11680
             → items[]: kaptCode, kaptName, bjdCode(10자리), as1~as3
- 기본 정보  GET apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusBassInfoV5?kaptCode=
             → item: kaptdaCnt(세대수), kaptUsedate(YYYYMMDD), kaptAddr(지번 주소), doroJuso, kaptDongCnt,
               kaptTopFloor, kaptBcompany, codeHeatNm, codeSaleNm, kaptMparea60/85/135/136
- 상세 정보  GET apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusDtlInfoV5?kaptCode=   (2026-10-14 확인)
             → item: subwayLine, subwayStation, kaptdWtimesub(역 도보 "5분이내"), kaptdWtimebus, kaptdPcnt/kaptdPcntu(지상/지하 주차),
               groundElChargerCnt, undergroundElChargerCnt, kaptdCccnt(CCTV), welfareFacility

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
from difflib import SequenceMatcher
from datetime import date

from collector.sources.molit import ApiError, QuotaExceeded, conn_failed, conn_pause, note_ok

LIST_URL = "https://apis.data.go.kr/1613000/AptListService4/getSigunguAptList4"
INFO_URL = "https://apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusBassInfoV5"
DETAIL_URL = "https://apis.data.go.kr/1613000/AptBasisInfoServiceV5/getAphusDtlInfoV5"


def _get_json(url: str, params: dict, retries: int = 5) -> dict:
    key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    full = url + "?" + urllib.parse.urlencode({"serviceKey": key, **params})
    while True:
        body = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(full, timeout=40) as r:
                    body = r.read().decode("utf-8")
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    raise QuotaExceeded("HTTP 429") from None
                raise ApiError(f"HTTP {e.code}") from None
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                if attempt < retries - 1:
                    time.sleep(2 * 2**attempt)
        if body is not None:
            break
        if not conn_pause():
            raise conn_failed()
    note_ok()
    if body.lstrip().startswith("<"):  # 게이트웨이 오류는 XML 로 온다
        if "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in body:
            raise QuotaExceeded("daily quota")
        raise ApiError(re.sub(r"\s+", " ", body)[:200])
    try:
        j = json.loads(body)
    except json.JSONDecodeError:
        raise ApiError("invalid json: " + re.sub(r"\s+", " ", body)[:120]) from None
    if not isinstance(j, dict) or "response" not in j:  # 2026-10-13 info 800건째에 이런 응답 1건으로 작업 전체가 KeyError 로 죽었다
        if "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in body:
            raise QuotaExceeded("daily quota")
        raise ApiError("unexpected body: " + re.sub(r"\s+", " ", body)[:120])
    code = j.get("response", {}).get("header", {}).get("resultCode")
    if code not in ("00", "000", None):
        msg = j["response"]["header"].get("resultMsg", "")
        if code == "22":
            raise QuotaExceeded(msg)
        raise ApiError(f"resultCode={code} {msg}")
    return j


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


def fetch_detail(kapt_code: str) -> dict | None:
    return _get_json(DETAIL_URL, {"kaptCode": kapt_code})["response"]["body"].get("item")


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
        # 세대수(kaptdaCnt)가 0인 단지가 있다(2026-10-19 센트라스: 세대수 0, 호수 2,529, 면적별 세대수도 0) → 호수로
        "households": _int(item.get("kaptdaCnt")) or _int(item.get("hoCnt")),
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


def _txt(v) -> str | None:
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    return v or None


def detail_row(item: dict) -> dict:
    """상세 정보 응답 → kapt_complexes 열 (0021)."""
    ev = [_int(item.get(k)) for k in ("groundElChargerCnt", "undergroundElChargerCnt")]
    return {
        "subway_line": _txt(item.get("subwayLine")),
        "subway_station": _txt(item.get("subwayStation")),
        "walk_subway": _txt(item.get("kaptdWtimesub")),
        "walk_bus": _txt(item.get("kaptdWtimebus")),
        "parking_ground": _int(item.get("kaptdPcnt")),
        "parking_under": _int(item.get("kaptdPcntu")),
        "ev_charger": None if all(x is None for x in ev) else sum(x or 0 for x in ev),
        "cctv": _int(item.get("kaptdCccnt")),
        "welfare": _txt(item.get("welfareFacility")),
    }


def walk_minutes(s: str | None) -> int | None:
    """도보 시간 구간 → 상한(분). '5분이내' 5, '5~10분이내' 10, '10~15분이내' 15, '20분초과' 99. 모르면 None."""
    if not s:
        return None
    s = s.replace(" ", "")
    if "초과" in s:
        return 99
    nums = re.findall(r"\d+", s)
    return int(nums[-1]) if nums and "분" in s else None


STATION_WALK_MIN = 10  # 📖 역까지 10분(700m) 이내 = 역세권 p.220


def station_area(s: str | None) -> bool | None:
    """H1 역세권: 도보 시간 상한이 10분 이하."""
    m = walk_minutes(s)
    return None if m is None else m <= STATION_WALK_MIN


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


_TOKEN = re.compile(r"[가-힣a-z]{2,}")
_ORD = re.compile(r"(?<![0-9])([0-9]{1,2})(?![0-9])")
_GENERIC = {"아파트", "단지", "마을", "apt"}


def _ords(s: str) -> set[str]:
    return set(_ORD.findall(s.replace("-", " ")))


def _narrow(cands: list[dict], name: str) -> dict | None:
    """같은 지번·도로명에 K-apt 단지가 여럿일 때 하나로 좁힌다. 좁혀지지 않으면 None.
    1) 임대 동 빼기(실거래는 분양분만 있다) 2) 이름 속 차수·단지 번호 3) 다른 후보엔 없는 이름 조각(건설사 등)
    'A,B'처럼 여러 단지를 묶은 이름은 하나만 고르면 세대수가 작게 잡히므로 1)만 한다."""
    pool = cands
    if "임대" not in name:
        pool = [k for k in pool if k.get("sale_type") != "임대" and "임대" not in (k["kapt_name"] or "")] or pool
    if "," in name:
        return pool[0] if len(pool) == 1 else None
    if len(pool) > 1:
        n = _ords(name)
        hit = [k for k in pool if n & _ords(k["kapt_name"] or "")]
        pool = hit or pool
    if len(pool) > 1:
        toks = [t for t in _TOKEN.findall(name.lower()) if t not in _GENERIC]
        score = [sum(t in norm_name(k["kapt_name"]) for t in toks) for k in pool]
        if max(score) > min(score):
            pool = [k for k, x in zip(pool, score) if x == max(score)]
    return pool[0] if len(pool) == 1 else None


@dataclass(frozen=True)
class Match:
    kapt_code: str
    method: str  # 'jibun' | 'road' | 'name' | 'fuzzy'


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
        if len(named) == 1:
            return named[0]
        return _narrow(cands, name)

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
        k = named[0] if len(named) == 1 else (_narrow(named, name) if named else None)
        if k:
            out[c["apt_seq"]] = Match(k["kapt_code"], "name")
    # 마지막: 같은 법정동에서 아직 아무 단지와도 안 이어진 K-apt 단지 중 이름이 가장 비슷한 곳(🔧 유사도 0.8+(0.75 는 서초프라임빌 ↔ 서초프라임헤센 오연결), 또는 0.6+ 이고 지번 본번이 같음,
    # 다음 후보보다 0.2 이상 높을 때만, 임대 제외). 2026-10-20 바쁜 미연결 155곳 중 'e편한세상초지역센트럴포레 ↔ 이편한세상 초지역 센트럴포레아파트' 등
    used = {m.kapt_code for m in out.values()}
    for c in complexes:
        if c["apt_seq"] in out:
            continue
        n = _fuzzy_key(c["apt_name"])
        cands = [k for k in by_bjd.get(c.get("bjd_code") or "", [])
                 if k["kapt_code"] not in used and k.get("sale_type") != "임대" and "임대" not in (k["kapt_name"] or "")]
        sc = sorted(((SequenceMatcher(None, n, _fuzzy_key(k["kapt_name"])).ratio(), k) for k in cands), key=lambda x: -x[0])
        if not sc or (len(sc) > 1 and sc[1][0] > sc[0][0] - 0.2):
            continue
        best, k = sc[0]
        same_main = norm_jibun(c.get("jibun")).split("-")[0] == jibun_from_addr(k.get("addr")).split("-")[0] != ""
        if best >= 0.8 or (best >= 0.6 and same_main):
            out[c["apt_seq"]] = Match(k["kapt_code"], "fuzzy")
            used.add(k["kapt_code"])
    return out


_SYN = (("e편한세상", "이편한세상"), ("lg", "엘지"), ("sk", "에스케이"), ("kcc", "케이씨씨"), ("gs", "지에스"))


def _fuzzy_key(s: str | None) -> str:
    n = norm_name(s)
    for a, b in _SYN:
        n = n.replace(a, b)
    return n
