"""H5 정비사업 단계 (경기): 경기데이터드림 '일반 정비 사업 추진 현황'(infId S62GFEEN7JMLMA0PH6CF19108891, 매일 갱신) CSV.
2026-10-20 사용자가 PC 에서 받은 파일로 확인: cp949, 533개 구역, 53열. openapi.gg.go.kr 는 해외 IP 차단이라 파일로 넣는다.
1기 신도시 특별법(노후계획도시) 사업은 이 자료에 없다(일반 정비사업만).

서울(collector/redev.py)과 같은 redev_zone 열로 바꾼다. 단계 이름은 서울 STAGE_ORDER 에 맞추고, 서울에 없는 '예정구역'(정비예정구역)은 0,
'청산'은 준공 뒤 절차라 준공(8)으로 본다.
"""

from __future__ import annotations

import csv
import io
import re

STAGE = {"예정구역": ("예정구역", 0), "정비구역": ("구역지정", 1), "추진위원회": ("추진위", 2), "조합설립": ("조합설립", 3),
         "사업시행": ("사업시행", 5), "관리처분": ("관리처분", 6), "착공": ("착공", 7), "준공": ("준공", 8), "청산": ("준공", 8)}
DATES = {"정비구역지정일자(최초지정)": "zone_ymd", "추진위승인일자": "committee_ymd", "조합설립인가일자": "assoc_ymd",
         "사업시행인가일자": "impl_ymd", "관리처분인가일자": "mgmt_ymd", "착공일자": "construction_ymd"}
INTS = {"(기존주택)세대수": "existing_hh", "사업시행세대수총계": "built_hh", "조합원분양세대수": "member_hh",
        "일반분양세대수": "gen_hh", "임대세대수": "rent_hh"}


def read(raw: bytes) -> list[dict]:
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("CSV 인코딩을 읽지 못함 (utf-8·cp949 아님)")
    rows = list(csv.DictReader(io.StringIO(text)))
    need = {"시군명", "사업단계", "사업유형", "정비구역명", "위치"}
    if not rows or not need <= set(rows[0]):
        raise ValueError(f"열 이름이 다름: {sorted(need - set(rows[0] if rows else []))} 없음")
    return rows


def _int(s: str | None) -> int | None:
    s = (s or "").replace(",", "").strip()
    try:
        return int(float(s)) if s else None
    except ValueError:
        return None


def _pct(s: str | None) -> float | None:
    m = re.match(r"\s*([\d.]+)\s*%?", s or "")
    return float(m.group(1)) if m else None


def _date(s: str | None) -> str | None:
    s = re.sub(r"\D", "", s or "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s[:2] in ("19", "20") else None


def parse_addr(s: str | None, city: str) -> tuple[str | None, str | None, int | None, int | None]:
    """'경기도 고양시 덕양구 관산동 178-57번지 일원' → ('덕양구', '관산동', 178, 57).
    '경기도 화성시 향남읍 행정리 123' → (None, '향남읍 행정리', 123, 0). 산 지번은 본번·부번 None."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    if s.lower().endswith("nan"):
        return None, None, None, None
    paren = re.findall(r"\(([^)]*)\)", s)
    s = re.sub(r"^(경기도|경기)\s*", "", s)
    while s.startswith(city):                       # '군포시 군포시 당동' 처럼 시 이름이 두 번 나오는 행이 있다
        s = s[len(city):].strip()
    gu = None
    m = re.match(r"([가-힣]+구)\s+", s)
    if m:
        gu, s = m.group(1), s[m.end():]
    m = re.match(r"((?:[가-힣]+[읍면]\s+)?(?:[가-힣]+\d*(?:동|리)|[가-힣]+\d+가))\s*(산\s*)?(\d+)?(?:-(\d+))?", s)
    if not m or not m.group(3) and not m.group(2):
        for p in paren:                              # 도로명 주소 뒤 괄호 '(단대동 177)'
            g2, u2, b2, j2 = parse_addr(p, city)
            if u2:
                return gu or g2, u2, b2, j2
    if not m:
        return gu, None, None, None
    umd = re.sub(r"([가-힣])\d+동$", r"\1동", m.group(1))     # 행정동 번호 → 법정동
    if m.group(2) or not m.group(3):
        return gu, umd, None, None
    return gu, umd, int(m.group(3)), int(m.group(4) or 0)


def zone_row(r: dict) -> dict:
    city = r["시군명"].strip()
    stage, no = STAGE.get(r["사업단계"].strip(), (r["사업단계"].strip() or None, None))
    gu, umd, bun, ji = parse_addr(r["위치"], city)
    out = {"code": f"GG-{city}-{r['정비구역명'].strip()}", "src": "gg", "district": city, "gu": gu,
           "zone_nm": r["정비구역명"].strip(), "jibun_addr": r["위치"].strip(), "road_addr": None, "umd_name": umd, "bun": bun, "ji": ji,
           "public_private": None, "general_promoted": None, "biz_type": r["사업유형"].strip() or None, "stage": stage, "stage_no": no,
           "sale_hh": None, "migration_ymd": None, "vl_old": _pct(r.get("(기존)용적률")), "vl_new": _pct(r.get("(신축)용적률")),
           "old_built": (r.get("(기존주택)준공년도") or "").strip() or None}
    out.update({v: _int(r.get(k)) for k, v in INTS.items()})
    out.update({v: _date(r.get(k)) for k, v in DATES.items()})
    if out["member_hh"] is not None and out["gen_hh"] is not None:
        out["sale_hh"] = out["member_hh"] + out["gen_hh"]
    return out


def region_code(z: dict, regions: dict[str, str], umd_region: dict[tuple[str, str], str]) -> str | None:
    """시군(+구) 이름으로 시군구 코드. 구가 있는 시인데 주소에 구가 없으면 같은 시의 단지 법정동으로 찾는다."""
    cands = {c: n for c, n in regions.items() if c.startswith("41") and n.split()[1] == z["district"]}
    if len(cands) == 1:
        return next(iter(cands))
    if z["gu"]:
        hit = [c for c, n in cands.items() if n.endswith(" " + z["gu"])]
        if len(hit) == 1:
            return hit[0]
    hit = {umd_region.get((c, z["umd_name"])) for c in cands} - {None}
    return hit.pop() if len(hit) == 1 else None


def full_umd(z: dict, regions: dict[str, str], cx_umd: list[dict]) -> str | None:
    """'상신리'처럼 읍·면 없이 적힌 리 → 같은 시 단지 법정동 '향남읍 상신리'(하나뿐일 때). 화성시 행이 이렇게 적혀 있다(2026-10-20)."""
    u = z["umd_name"]
    if not u or not u.endswith("리") or " " in u:
        return u
    codes = {c for c, n in regions.items() if c.startswith("41") and n.split()[1] == z["district"]}
    hit = {r["umd_name"] for r in cx_umd if r["region_code"] in codes and (r["umd_name"] or "").endswith(" " + u)}
    return hit.pop() if len(hit) == 1 else u
