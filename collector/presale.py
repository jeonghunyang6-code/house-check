"""청약홈 APT 분양정보 → 입주 물량 F1 (순수 함수, jobs/presale.py).

API: 한국부동산원 청약홈 분양정보 조회 서비스 getAPTLttotPblancDetail (api.odcloud.kr, 공공데이터포털 키).
2026-10-16 GitHub 러너에서 확인: 서울 195·경기 918·인천 225건, 가장 오래된 공고 2020-12. 칸: HOUSE_MANAGE_NO, HOUSE_NM,
HSSPLY_ADRES(공급 위치), TOT_SUPLY_HSHLDCO(공급 세대 = 일반+특별공급. **재건축·재개발 조합원 몫은 빠짐**), MVN_PREARNGE_YM(입주 예정 YYYYMM),
RCRIT_PBLANC_DE(모집공고일), HOUSE_SECD_NM, HOUSE_DTL_SECD_NM, SUBSCRPT_AREA_CODE_NM.
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
            "area": (it.get("SUBSCRPT_AREA_CODE_NM") or "").strip()}


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
