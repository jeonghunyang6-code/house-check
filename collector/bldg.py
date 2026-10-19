"""H5 재건축 사업성 재료: 건축물대장 (국토교통부 건축HUB 건축물대장정보, 2026-10-19 활용 승인·실제 응답 확인).
📖 재건축 사업성 = 용적률 낮고 대지지분 크고 분양가 높고 일반분양 많을수록 p.374~397.

- 총괄표제부(getBrRecapTitleInfo): 단지 전체. platArea 대지면적, vlRat 용적률, vlRatEstmTotArea 용적률 산정용 연면적, hhldCnt 세대수
- 총괄표제부가 없으면(동 하나짜리 등) 표제부(getBrTitleInfo) 공동주택 동을 합친다
- 오래된 단지는 대지면적·용적률이 0 으로 비어 있는 경우가 많다(2026-10-19 2000년 이전 표본: 총괄표제부 22곳 중 9곳, 은마도 0).
  대지면적이 있으면 용적률 = 산정용 연면적 ÷ 대지면적 으로 계산해 둔다(vl_rat_calc). 대지지분(세대당 대지면적) = 대지면적 ÷ 세대수
"""

from __future__ import annotations

from collector.kapt import _get_json

RECAP_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrRecapTitleInfo"
TITLE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"


def params(bjd_code: str, jibun: str) -> dict | None:
    """법정동 코드 10자리 + 지번('316', '12-3') → 조회 인자. 산 지번·이상한 지번은 None."""
    main, _, sub = (jibun or "").partition("-")
    if len(bjd_code or "") != 10 or not main.isdigit() or (sub and not sub.isdigit()):
        return None
    return {"sigunguCd": bjd_code[:5], "bjdongCd": bjd_code[5:], "platGbCd": "0", "bun": main.zfill(4), "ji": (sub or "0").zfill(4)}


def _items(j: dict) -> list[dict]:
    b = j["response"]["body"]
    it = (b.get("items") or {}).get("item") if isinstance(b.get("items"), dict) else None
    return (it if isinstance(it, list) else [it]) if it else []


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _row(src: str, plat: float, vl: float, estm: float, tot: float, hh: int, nb: int) -> dict:
    calc = round(estm / plat * 100, 1) if plat > 0 and estm > 0 else None
    return {"src": src, "plat_area": plat or None, "vl_rat": vl or None, "vl_rat_calc": calc, "estm_area": estm or None,
            "tot_area": tot or None, "hhld": hh or None, "main_bld": nb or None,
            "land_per_hh": round(plat / hh, 1) if plat > 0 and hh > 0 else None}


def recap_row(items: list[dict]) -> dict | None:
    """총괄표제부 → 행. 여러 개면 세대수가 가장 많은 것."""
    if not items:
        return None
    x = max(items, key=lambda i: _f(i.get("hhldCnt")))
    return _row("recap", _f(x.get("platArea")), _f(x.get("vlRat")), _f(x.get("vlRatEstmTotArea")), _f(x.get("totArea")),
                int(_f(x.get("hhldCnt"))), int(_f(x.get("mainBldCnt"))))


def title_row(items: list[dict]) -> dict | None:
    """표제부(동별) → 행. 공동주택 동만, 대지면적은 동마다 같은 값이 적히거나 0 이라 가장 큰 값."""
    apt = [i for i in items if "공동주택" in (i.get("mainPurpsCdNm") or "") or _f(i.get("hhldCnt")) > 0]
    if not apt:
        return None
    vl = max(_f(i.get("vlRat")) for i in apt)
    return _row("title", max(_f(i.get("platArea")) for i in apt), vl, sum(_f(i.get("vlRatEstmTotArea")) for i in apt),
                sum(_f(i.get("totArea")) for i in apt), int(sum(_f(i.get("hhldCnt")) for i in apt)), len(apt))


def fetch(bjd_code: str, jibun: str) -> dict:
    p = params(bjd_code, jibun)
    if p is None:
        return {"src": "none"}
    r = recap_row(_items(_get_json(RECAP_URL, {**p, "numOfRows": 10, "pageNo": 1, "_type": "json"})))
    if r is None:
        r = title_row(_items(_get_json(TITLE_URL, {**p, "numOfRows": 100, "pageNo": 1, "_type": "json"})))
    return r or {"src": "none"}
