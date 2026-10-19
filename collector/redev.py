"""H5 정비사업 단계 (서울): 서울 열린데이터광장 '서울특별시 도시정비사업 통계'(OA-22856, 오픈 API TbSeoulRedevStatus, 분기 갱신,
2026-10-19 러너에서 확인: 496개 구역, 25개 구). SEOUL_API_KEY. 이 클라우드 세션에서는 data.seoul.go.kr 이 막혀 Actions 에서 받는다.

📖 재개발은 조합설립인가 이후 매수, 노후도 미충족이면 불가, 가장 큰 리스크는 시간 p.368~373
📖 재건축: 상급지는 절차 무관, 중·하급지는 조합설립인가 후. 기간 20~25년 p.374~397
단지 연결: 재건축 구역의 지번(시군구·법정동·본번)이 같은 실거래 단지. 행정동 표기('쌍문2동')는 법정동('쌍문동')으로 바꿔 본다
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from collector.kapt import norm_name

URL = "http://openapi.seoul.go.kr:8088/{key}/json/TbSeoulRedevStatus/{a}/{b}/"
STAGE_ORDER = ("구역지정", "추진위", "조합설립", "사업시행", "관리처분", "착공", "준공")
REBUILD = ("공동주택재건축", "아파트지구재건축")
FIELDS = {   # API 열 → 우리 열
    "CODE": "code", "DISTRICT": "district", "ZONE_NM": "zone_nm", "JIBUN_ADDR": "jibun_addr", "ROAD_ADDR": "road_addr",
    "BIZ_METHOD_PUBLIC_PRIVATE": "public_private", "BIZ_METHOD_GENERAL_PROMOTED": "general_promoted", "BIZ_TYPE": "biz_type",
    "BIZ_STAGE": "stage", "EXISTING_HOUSEHOLDS": "existing_hh", "TOT_BUILT_HOUSEHOLDS": "built_hh",
    "SALE_BUILT_HOUSEHOLDS": "sale_hh", "RENT_BUILT_HOUSEHOLDS": "rent_hh",
    "ZONE_DESIGNATION_INIT_YMD": "zone_ymd", "PROMOTION_COMMITTEE_YMD": "committee_ymd", "ASSOCIATION_ESTABLISHMENT_YMD": "assoc_ymd",
    "BIZ_IMPLEMENTATION_INIT_YMD": "impl_ymd", "MGMT_DISPOSITION_INIT_YMD": "mgmt_ymd", "MIGRATION_START_YMD": "migration_ymd",
    "CONSTRUCTION_START_YMD": "construction_ymd",
}
INT_COLS = ("existing_hh", "built_hh", "sale_hh", "rent_hh")


def fetch_all(page: int = 1000) -> list[dict]:
    key, out, a = os.environ["SEOUL_API_KEY"], [], 1
    while True:
        with urllib.request.urlopen(URL.format(key=key, a=a, b=a + page - 1), timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
        x = d.get("TbSeoulRedevStatus")
        if not x:
            res = d.get("RESULT", {})
            if res.get("CODE") == "INFO-200":      # 데이터 없음
                return out
            raise RuntimeError(f"서울 API {res.get('CODE')} {res.get('MESSAGE')}")
        out += x.get("row", [])
        if len(out) >= int(x.get("list_total_count", 0)) or not x.get("row"):
            return out
        a += page


def parse_addr(s: str | None) -> tuple[str, int, int] | None:
    """'양천구목동903' → ('목동', 903, 0), '쌍문2동 81번지' → ('쌍문동', 81, 0), '효창동 5-307' → ('효창동', 5, 307). 산 지번은 None."""
    s = re.sub(r"\s+", "", s or "")
    s = re.sub(r"^(서울특별시|서울시|서울)", "", s)
    s = re.sub(r"^[가-힣]{1,4}구(?=[가-힣])", "", s)
    s = re.sub(r"([가-힣])\d+동", r"\1동", s)            # 행정동 번호 → 법정동
    m = re.match(r"([가-힣]+(?:동|가|로)(?:\d+가)?)(\d+)(?:-(\d+))?", s)
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3) or 0)


def zone_row(r: dict, regions: dict[str, str]) -> dict:
    out = {v: (r.get(k) or "").strip() or None for k, v in FIELDS.items()}
    for c in INT_COLS:
        out[c] = int(out[c]) if out[c] and out[c].isdigit() else None
    for c in [v for v in FIELDS.values() if v.endswith("_ymd")]:
        out[c] = out[c] if out[c] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", out[c]) else None
    out["region_code"] = next((c for c, n in regions.items() if n == f"서울 {out['district']}"), None)
    p = parse_addr(out["jibun_addr"])
    out["umd_name"], out["bun"], out["ji"] = p if p else (None, None, None)
    out["stage_no"] = STAGE_ORDER.index(out["stage"]) + 1 if out["stage"] in STAGE_ORDER else None
    return out


def link(zones: list[dict], complexes: list[dict]) -> list[tuple[str, str, str]]:
    """재건축 구역 → 실거래 단지 [(apt_seq, code, how)]. complexes: apt_seq, apt_name, region_code, umd_name, jibun.
    지번 본번이 같은 단지(how='jibun'), 없으면 같은 동에서 이름이 서로 포함되는 단지(how='name')."""
    by: dict[tuple[str, str], list[dict]] = {}
    for c in complexes:
        by.setdefault((c["region_code"], c["umd_name"]), []).append(c)
    out = []
    for z in zones:
        if z["biz_type"] not in REBUILD or not z["umd_name"]:
            continue
        cands = by.get((z["region_code"], z["umd_name"]), [])
        hit = [c for c in cands if (c["jibun"] or "").split("-")[0].isdigit() and int(c["jibun"].split("-")[0]) == z["bun"]]
        how = "jibun"
        if not hit:
            zn = norm_name(z["zone_nm"])
            hit = [c for c in cands if len(norm_name(c["apt_name"])) >= 2 and (norm_name(c["apt_name"]) in zn or zn in norm_name(c["apt_name"]))]
            how = "name"
        out += [(c["apt_seq"], z["code"], how) for c in hit]
    return out
