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
from collector.regions import REGIONS

SEOUL_GU = tuple(sorted((n.split()[1] for c, n in REGIONS.items() if c.startswith("11")), key=len, reverse=True))

URL = "http://openapi.seoul.go.kr:8088/{key}/json/TbSeoulRedevStatus/{a}/{b}/"
STAGE_ORDER = ("구역지정", "추진위", "조합설립", "건축심의", "사업시행", "관리처분", "착공", "준공")   # 2026-10-19 실제 값 7개(준공 없음)
REBUILD = ("공동주택재건축", "아파트지구재건축", "재건축")   # 마지막은 경기(collector/redev_gg.py) 표기
DONE = 8   # 준공(경기 자료의 준공·청산). 끝난 구역은 단지에 잇지 않는다(새 단지에 '정비 준공'이 붙지 않게)
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
    for gu in SEOUL_GU:                                   # 구 이름은 목록으로만 뗀다('압구정동'의 '압구'를 떼지 않게)
        if s.startswith(gu):
            s = s[len(gu):]
            break
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


def _key(name: str, umd: str) -> str:
    """이름 비교용: 괄호·'아파트' 빼고, 앞의 동 이름('역삼동', '역삼')을 뗀다."""
    n = norm_name(name)
    for p in (umd, umd[:-1] if umd.endswith("동") else umd):
        if p and n.startswith(p):
            return n[len(p):]
    return n


def _jibun(s: str | None) -> tuple[int, int] | None:
    main, _, sub = (s or "").partition("-")
    return (int(main), int(sub or 0)) if main.isdigit() and (not sub or sub.isdigit()) else None


def link(zones: list[dict], complexes: list[dict]) -> list[tuple[str, str, str]]:
    """재건축 구역 → 실거래 단지 [(apt_seq, code, how)]. complexes: apt_seq, apt_name, region_code, umd_name, jibun.
    ① 지번(본번·부번)이 같은 단지 — 여럿이면 이름이 겹치는 단지만(겹치는 게 없으면 다)
    ② 없으면 같은 동에서 이름이 겹치는 단지(동 이름을 뗀 뒤 🔧 3글자 이상 포함). 본번만 같은 단지는 이름도 겹칠 때만
    (이촌동 300번지처럼 한 본번에 단지가 여럿인 곳이 있어 본번만으로는 잇지 않는다)
    사업이 시작된 해(추진위·조합설립·사업시행 등 가장 이른 날짜. 구역 지정은 여의도 아파트지구 1976 처럼 단지보다 앞설 수 있어 뺀다) 이후에 지은 단지는 그 구역이 새로 지은 단지라 잇지 않는다
    (2026-10-20 경기 '인정프린스아파트' 착공 구역이 같은 지번의 2025년 새 단지에 이어졌다)"""
    by: dict[tuple[str, str], list[dict]] = {}
    for c in complexes:
        by.setdefault((c["region_code"], c["umd_name"]), []).append(c)
    out = []
    for z in zones:
        if z["biz_type"] not in REBUILD or not z["umd_name"] or z.get("stage_no") == DONE:
            continue
        ys = [str(z[k])[:4] for k in ("committee_ymd", "assoc_ymd", "impl_ymd", "mgmt_ymd", "construction_ymd") if z.get(k)]
        start = int(min(ys)) if ys else None
        cands = [c for c in by.get((z["region_code"], z["umd_name"]), [])
                 if not (start and c.get("build_year") and int(c["build_year"]) >= start)]
        zk = _key(z["zone_nm"] or "", z["umd_name"])

        def named(cs):
            return [c for c in cs if (lambda k: len(min(k, zk, key=len)) >= 3 and (k in zk or zk in k))(_key(c["apt_name"], z["umd_name"]))]
        exact = [c for c in cands if _jibun(c["jibun"]) == (z["bun"], z["ji"] or 0)]
        if exact:
            hit, how = named(exact) or exact, "jibun"
        else:
            hit, how = named(cands), "name"
        out += [(c["apt_seq"], z["code"], how) for c in hit]
    return out


def general_sale(zones: list[dict]) -> dict[str, tuple[int, float, float]]:
    """재건축 구역 일반분양 {code: (세대, ÷기존 세대, 같은 시도 재건축 구역 중 백분위)}. 기존 세대가 있고 일반분양을 알 수 있는 곳만.
    경기는 원자료의 일반분양 세대(gen_hh), 서울은 계획 분양 세대 − 기존 세대 근사. 끝난(준공) 구역은 순위에서 뺀다.
    📖 재건축 사업성은 일반분양이 많을수록 좋다 p.374~397 — 작가 기준 숫자는 없어 순위만"""
    rows = {}
    for z in zones:
        ex = z.get("existing_hh") or 0
        if z["biz_type"] not in REBUILD or ex <= 0 or z.get("stage_no") == DONE:
            continue
        if z.get("gen_hh") is not None:
            g = z["gen_hh"]
        elif (z.get("sale_hh") or 0) > 0:
            g = z["sale_hh"] - ex
        else:
            continue
        rows[z["code"]] = ((z.get("region_code") or "")[:2], g, g / ex)
    out = {}
    for sido in {v[0] for v in rows.values()}:
        rs = sorted(r for s_, _, r in rows.values() if s_ == sido)
        out.update({c: (g, round(r, 2), round(sum(1 for x in rs if x <= r) * 100 / len(rs), 1))
                    for c, (s_, g, r) in rows.items() if s_ == sido})
    return out
