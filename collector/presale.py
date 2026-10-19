"""청약홈 APT 분양정보 → 입주 물량 F1 (순수 함수, jobs/presale.py).

API: 한국부동산원 청약홈 분양정보 조회 서비스 getAPTLttotPblancDetail (api.odcloud.kr, 공공데이터포털 키).
2026-10-16 GitHub 러너에서 확인: 서울 195·경기 918·인천 225건, 가장 오래된 공고 2020-12. 칸: HOUSE_MANAGE_NO, HOUSE_NM,
HSSPLY_ADRES(공급 위치), TOT_SUPLY_HSHLDCO(공급 세대 = 일반+특별공급. **재건축·재개발 조합원 몫은 빠짐**), MVN_PREARNGE_YM(입주 예정 YYYYMM),
RCRIT_PBLANC_DE(모집공고일), HOUSE_SECD_NM, HOUSE_DTL_SECD_NM, SUBSCRPT_AREA_CODE_NM, IMPRMN_BSNS_AT(정비사업 Y/N).

총 세대 보정(2026-10-16): 청약홈에는 총 세대가 없다(입지톡도 같은 49칸). 입주한 단지는 K-apt 세대수로 바꾸고(match_complex),
아직 입주 전인 정비사업 공고는 입주한 정비사업 공고들의 'K-apt 세대 ÷ 공급 세대' 중앙값을 곱해 추정한다(🔧, 데이터로 정한 비율).
"""

from __future__ import annotations

import re

AREAS = ("서울", "경기", "인천")


def parse_item(it: dict) -> dict | None:
    ym = str(it.get("MVN_PREARNGE_YM") or "").strip()
    if not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", ym) or not it.get("HOUSE_MANAGE_NO"):
        return None
    try:
        hh = int(it.get("TOT_SUPLY_HSHLDCO") or 0)
    except (TypeError, ValueError):
        hh = 0
    return {"house_no": str(it["HOUSE_MANAGE_NO"]), "name": (it.get("HOUSE_NM") or "").strip(),
            "address": (it.get("HSSPLY_ADRES") or "").strip(), "households": hh, "move_in_ym": ym,
            "notice_date": it.get("RCRIT_PBLANC_DE") or None, "house_type": (it.get("HOUSE_SECD_NM") or "").strip(),
            "area": (it.get("SUBSCRPT_AREA_CODE_NM") or "").strip(), "imprmn": str(it.get("IMPRMN_BSNS_AT") or "").upper() == "Y"}


def address_candidates(addr: str) -> list[tuple[str, str]]:
    """'서울특별시 성북구 하월곡동 70-4번지 일원' → [('jibun', '서울특별시 성북구 하월곡동 70-4'), ('dong', '서울특별시 성북구 하월곡동')].
    여러 동에 걸친 공공택지(쉼표)는 첫 동만. 동까지만 찾으면 좌표가 동 중심이라 geo_method='dong' 으로 표시한다."""
    a = re.sub(r"\(.*?\)", " ", addr or "")
    a = a.split(",")[0]
    a = re.sub(r"\s*(번지)?\s*(일원|일대|외\s*\d*\s*필지|외)\b.*$", "", a)
    a = re.sub(r"번지", "", a)
    a = re.sub(r"\s+", " ", a).strip()
    toks = a.split()
    dong = next((" ".join(toks[: i + 1]) for i, t in enumerate(toks) if i >= 2 and re.search(r"(동|가|리|읍|면)$", t)
                 and not (i + 1 < len(toks) and re.search(r"(동|가|리)$", toks[i + 1]))), None)
    out = [("jibun", a)] if re.search(r"\d", a) and a != dong else []
    if dong:
        out.append(("dong", dong))
    return out


def month_add(ym: str, k: int) -> str:
    y, m = int(ym[:4]), int(ym[4:6]) - 1 + k
    return f"{y + m // 12}{m % 12 + 1:02d}"


MATCH_M = 500      # 🔧 공고 좌표와 단지 좌표 거리
NAME_RUN = 3       # 🔧 이름이 이만큼 이어서 같으면 같은 단지로 본다


def norm_name(s: str) -> str:
    return re.sub(r"\(.*?\)|아파트|\s|[^0-9A-Za-z가-힣]", "", s or "")


def name_overlap(a: str, b: str) -> int:
    """두 이름의 가장 긴 공통 연속 글자 수."""
    a, b = norm_name(a), norm_name(b)
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b:
                best = j - i
            else:
                break
    return best


def match_complex(p: dict, cands: list[dict], dist) -> dict | None:
    """입주한 공고 → K-apt 세대수가 있는 단지. cands: {name, lat, lng, build_year, households}. 거리 MATCH_M 안,
    준공 연도가 입주 예정 연도 ±1, 이름이 NAME_RUN 글자 이상 겹치는 단지 중 가장 가까운 것."""
    if p.get("lat") is None:
        return None
    y = int(p["move_in_ym"][:4])
    ok = []
    for c in cands:
        if abs(c["lat"] - p["lat"]) > 0.01 or abs(c["lng"] - p["lng"]) > 0.012 or not c.get("households"):
            continue
        if c.get("build_year") is None or abs(int(c["build_year"]) - y) > 1 or name_overlap(p["name"], c["name"]) < NAME_RUN:
            continue
        d = dist(p["lat"], p["lng"], c["lat"], c["lng"])
        if d <= MATCH_M:
            ok.append((d, c))
    return min(ok, key=lambda x: x[0])[1] if ok else None


DUP_NAME = re.compile(r"잔여|취소|무순위|임의공급|추가\s*모집|재공고|사후|계약\s*포기")


def total_households(rows: list[dict], matched: dict[str, tuple[int, str]]) -> tuple[float | None, dict[str, tuple[int, str]]]:
    """rows: 공고(house_no, name, households, imprmn). matched: house_no → (K-apt 세대, apt_seq).
    → (정비사업 비율 중앙값, house_no → (총 세대, 근거)).
    잔여·취소분 같은 다시 파는 공고(DUP_NAME)와 같은 단지에 맞춰진 두 번째 공고부터는 0(중복). 비율은 공급 30세대 이상
    입주 정비사업 공고로만 낸다(2026-10-16: 67건 중앙값 2.34, 10~90% 1.17~4.72 → 단지별 추정은 거칠다)."""
    from statistics import median
    dup = {r["house_no"] for r in rows if DUP_NAME.search(r.get("name") or "")}
    first: dict[str, str] = {}
    for r in sorted(rows, key=lambda r: -r["households"]):
        h = r["house_no"]
        if h in matched and h not in dup:
            seq = matched[h][1]
            if seq in first:
                dup.add(h)
            else:
                first[seq] = h
    rs = [matched[r["house_no"]][0] / r["households"] for r in rows
          if r["imprmn"] and r["house_no"] in matched and r["house_no"] not in dup and r["households"] >= 30]
    ratio = median(rs) if len(rs) >= 5 else None
    out = {}
    for r in rows:
        h = r["house_no"]
        if h in dup:
            out[h] = (0, "중복")
        elif h in matched:
            out[h] = (matched[h][0], "K-apt")
        elif r["imprmn"] and ratio:
            out[h] = (round(r["households"] * ratio), f"추정 ×{ratio:.2f}")
        else:
            out[h] = (r["households"], "공급")
    return ratio, out


# 한국부동산원 주택공급정보 입주 예정 물량 (공공데이터포털 15111714, 반기마다 새 파일, 2026-10-16 확인: 2026-06-30 기준
# 2026-07~2028-06 입주, 칸 입주예정월·지역·사업유형·주소·아파트명·세대수). 세대수는 조합원·임대 포함 총 세대(부동산원·R114 공표)
PLAN_FILE = "15111714"
SIDO = {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천"}


def parse_plan(text: str) -> list[dict]:
    import csv
    import io
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        if (r.get("지역") or "").strip() not in AREAS:
            continue
        ym = (r.get("입주예정월") or "").replace("-", "").strip()
        try:
            hh = int(float(r.get("세대수") or 0))
        except ValueError:
            continue
        if not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", ym) or hh <= 0:
            continue
        out.append({"name": (r.get("아파트명") or "").strip(), "address": (r.get("주소") or "").strip(), "area": r["지역"].strip(),
                    "kind": (r.get("사업유형") or "").strip(), "households": hh, "move_in_ym": ym})
    return out


def locate(addr: str, dong_index: dict, regions: dict) -> tuple[str | None, str | None]:
    """주소 → (시군구 코드, 생활권). dong_index: (시도 약칭, 법정동 이름) → Counter((region_code, lifezone_id)).
    법정동 이름은 '반포동'처럼 한 낱말이거나 '동탄면 영천리'처럼 두 낱말. 시군구 이름(특례시 → 시)이 주소에 있는 것만."""
    a = re.sub(r"특례시", "시", addr or "")
    toks = a.split()
    if not toks or toks[0] not in SIDO:
        return None, None
    sd = SIDO[toks[0]]
    for i in range(1, len(toks)):
        for j in (i + 2, i + 1):
            hit = dong_index.get((sd, " ".join(toks[i:j])))
            if not hit:
                continue
            ok = [(k, n) for k, n in hit.items() if all(t in a for t in regions.get(k[0], "").split()[1:])]
            if ok:
                (rc, z), _ = max(ok, key=lambda x: x[1])
                return rc, z
    return None, None


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_models(items: list[dict]) -> dict[str, dict]:
    """청약홈 주택형별(getAPTLttotPblancMdl) → 공고별 분양가 요약.
    HOUSE_TY '084.9800A' 의 숫자 = 전용면적(㎡), LTTOT_TOP_AMOUNT = 그 주택형 최고 분양가(만원), SUPLY_HSHLDCO(일반)·SPSPLY_HSHLDCO(특별) = 세대.
    ㎡당 분양가 = 주택형별 (최고가 ÷ 전용)의 세대 가중 중앙값. 84형 = 전용 80~89㎡ 주택형 최고가 중 가장 큰 값."""
    by: dict[str, list[tuple[float, float, int, float]]] = {}
    seen: set[str] = set()
    for it in items:
        h = str(it.get("HOUSE_MANAGE_NO") or "").strip()
        if not h:
            continue
        seen.add(h)
        m = re.match(r"\s*(\d+(?:\.\d+)?)", str(it.get("HOUSE_TY") or ""))
        area, price = (float(m.group(1)) if m else None), _num(it.get("LTTOT_TOP_AMOUNT"))
        if not area or area < 10 or not price or price <= 0:
            continue
        hh = int((_num(it.get("SUPLY_HSHLDCO")) or 0) + (_num(it.get("SPSPLY_HSHLDCO")) or 0)) or 1
        by.setdefault(h, []).append((price / area, area, hh, price))
    out = {}
    for h in seen:
        xs = sorted(by.get(h, []))
        if not xs:
            out[h] = dict(price_ppm_10k=None, price84_10k=None, price_types=0)
            continue
        tot, acc, med = sum(x[2] for x in xs), 0, xs[-1][0]
        for ppm, _, hh, _ in xs:
            acc += hh
            if acc * 2 >= tot:
                med = ppm
                break
        p84 = [x[3] for x in xs if 80 <= x[1] < 90]
        out[h] = dict(price_ppm_10k=round(med, 1), price84_10k=round(max(p84)) if p84 else None, price_types=len(xs))
    return out
