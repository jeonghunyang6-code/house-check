"""생활 인프라: 지하철역 위치 → 단지별 가장 가까운 역 (순수 함수, jobs/infra.py).

역 원본은 공공데이터포털 파일(노선·운영기관마다 따로, 열 이름이 제각각) → normalize_station 으로 (역명, 노선, 위도, 경도).
같은 이름(괄호·'역' 제외)이 500m 안에 있으면 한 역으로 합친다(환승역). 거리는 직선(하버사인), 📖 역세권 700m·10분 p.220.
입지는 점수화하지 않고 '왜 이 가격인가' 설명에만 쓴다(M3).
"""

from __future__ import annotations

import math
import re

NAME_KEYS = ("역명", "역사명", "역이름", "역 명")
LINE_KEYS = ("호선", "노선명", "선명", "관련노선", "노선")
LAT_KEYS = ("위도", "역위도", "위도좌표", "Y좌표", "y좌표")
LNG_KEYS = ("경도", "역경도", "경도좌표", "X좌표", "x좌표")
MERGE_M = 500.0
STATION_AREA_M = 700.0   # 📖 p.220


def _pick(row: dict, keys) -> str | None:
    for k in keys:
        for col, v in row.items():
            if col and col.strip() == k and str(v or "").strip():
                return str(v).strip()
    return None


def norm_name(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s or "").strip()
    return s[:-1] if s.endswith("역") and len(s) > 2 else s


def normalize_station(row: dict, line_default: str = "") -> dict | None:
    name, lat, lng = _pick(row, NAME_KEYS), _pick(row, LAT_KEYS), _pick(row, LNG_KEYS)
    try:
        la, lo = float(lat), float(lng)
    except (TypeError, ValueError):
        return None
    if la > lo:                       # 위도·경도가 뒤바뀐 파일
        la, lo = lo, la
    if not (33 < la < 39 and 124 < lo < 132) or not name:
        return None
    line = _pick(row, LINE_KEYS) or line_default
    if line and re.fullmatch(r"\d+", line):
        line = f"{line}호선"
    return {"name": norm_name(name), "line": line, "lat": la, "lng": lo}


def dist_m(la1: float, lo1: float, la2: float, lo2: float) -> float:
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def merge_stations(rows: list[dict]) -> list[dict]:
    """같은 이름이 MERGE_M 안이면 한 역(노선 합침, 좌표 평균)."""
    out: list[dict] = []
    for r in rows:
        hit = next((s for s in out if s["name"] == r["name"] and dist_m(s["lat"], s["lng"], r["lat"], r["lng"]) <= MERGE_M), None)
        if hit:
            if r["line"] and r["line"] not in hit["lines"]:
                hit["lines"].append(r["line"])
            n = hit["n"]
            hit["lat"], hit["lng"], hit["n"] = (hit["lat"] * n + r["lat"]) / (n + 1), (hit["lng"] * n + r["lng"]) / (n + 1), n + 1
        else:
            out.append({"name": r["name"], "lines": [r["line"]] if r["line"] else [], "lat": r["lat"], "lng": r["lng"], "n": 1})
    return out


def nearest(lat: float, lng: float, stations: list[dict]) -> tuple[dict | None, float | None]:
    best, bd = None, None
    for s in stations:
        if abs(s["lat"] - lat) > 0.05 or abs(s["lng"] - lng) > 0.06:   # 약 5km 밖은 건너뜀
            continue
        d = dist_m(lat, lng, s["lat"], s["lng"])
        if bd is None or d < bd:
            best, bd = s, d
    return best, (round(bd) if bd is not None else None)
