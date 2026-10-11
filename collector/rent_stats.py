"""전월세 원본 → 단지 × 면적군 × 계약월 요약 (rent_monthly, 0007). 원본 파일 행과 DB 행 모두 받는다."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import median


def _i(v) -> int | None:
    if v is None or v == "":
        return None
    return int(v)


def _med(xs: list[int]) -> int | None:
    return int(round(median(xs))) if xs else None


def summarize(rows: list[dict]) -> list[dict]:
    """rows: RENT_COLUMNS 를 가진 dict (값은 문자열이어도 된다). 사라진(disappeared) 행은 뺀다."""
    groups: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for r in rows:
        if str(r.get("disappeared", "")).lower() in ("1", "true"):
            continue
        groups[(r["apt_seq"], math.floor(float(r["area_m2"])), r["contract_month"])].append(r)
    out = []
    for (apt_seq, area_group, month), rs in sorted(groups.items()):
        jeonse = [r for r in rs if _i(r["monthly_rent_10k"]) == 0]
        wolse = [r for r in rs if _i(r["monthly_rent_10k"]) != 0]
        new = [r for r in jeonse if r["contract_type"] == "신규"]
        out.append({
            "apt_seq": apt_seq,
            "area_group": area_group,
            "contract_month": month,
            "region_code": rs[0]["region_code"],
            "apt_name": rs[0]["apt_name"],
            "n_jeonse": len(jeonse),
            "jeonse_median_10k": _med([_i(r["deposit_10k"]) for r in jeonse]),
            "n_jeonse_new": len(new),
            "jeonse_new_median_10k": _med([_i(r["deposit_10k"]) for r in new]),
            "n_jeonse_renew": sum(r["contract_type"] == "갱신" for r in jeonse),
            "n_wolse": len(wolse),
            "wolse_deposit_median_10k": _med([_i(r["deposit_10k"]) for r in wolse]),
            "wolse_rent_median_10k": _med([_i(r["monthly_rent_10k"]) for r in wolse]),
            "n_renewal_right_used": sum(str(r["used_renewal_right"]).lower() in ("1", "true") for r in rs),
            "n_type_blank": sum(r["contract_type"] in ("", None) for r in rs),
        })
    return out


def rent_to_row(key: str, region_code: str, contract_month: str, x, first_seen=None, last_seen=None) -> dict:
    """molit.Rent → RENT_COLUMNS dict (API 로 받은 과거 이력용: first/last_seen 없음)."""
    return {
        "rent_key": key, "region_code": region_code, "contract_month": contract_month, "apt_seq": x.apt_seq,
        "apt_name": x.apt_name, "contract_date": x.contract_date.isoformat(), "area_m2": x.area_m2,
        "floor": x.floor, "deposit_10k": x.deposit_10k, "monthly_rent_10k": x.monthly_rent_10k,
        "contract_type": x.contract_type or "", "used_renewal_right": x.used_renewal_right,
        "term_start": x.term_start.isoformat() if x.term_start else None,
        "term_end": x.term_end.isoformat() if x.term_end else None,
        "pre_deposit_10k": x.pre_deposit_10k, "pre_monthly_rent_10k": x.pre_monthly_rent_10k,
        "first_seen_date": first_seen, "last_seen_date": last_seen, "disappeared": False,
    }
