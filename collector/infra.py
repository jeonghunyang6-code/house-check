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
CONFLICT_M = 3000.0      # 같은 이름이 이 안에 따로 있으면 한쪽 좌표가 틀린 것 (2026-10-14 잠실새내: 한 출처가 1.8km 떨어진 좌표)
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


def drop_shared_coords(rows: list[dict]) -> list[dict]:
    """한 파일 안에서 이름이 다른 역이 좌표가 똑같으면 하나는 틀린 좌표다(경춘선 파일의 사릉 = 별내 좌표).
    다른 출처에서 같은 이름이 AGREE_M 안에 있는 역만 맞는 것으로 보고 나머지를 뺀다.
    아무도 확인되지 않으면 어느 쪽이 맞는지 몰라 그대로 둔다(마곡·발산 등). 단 같은 이름이 다른 출처에서 다른 자리로 나오면
    좌표를 공유한 쪽을 뺀다(2026-10-16: 1호선 파일의 청산 = 의정부 좌표, 카카오 보충 파일은 연천 청산면)."""
    groups: dict[tuple, set] = {}
    for r in rows:
        groups.setdefault((r["src"], r["lat"], r["lng"]), set()).add(r["name"])

    def confirmed(r):
        return any(o["src"] != r["src"] and o["name"] == r["name"]
                   and dist_m(r["lat"], r["lng"], o["lat"], o["lng"]) <= AGREE_M for o in rows)

    out = []
    for r in rows:
        names = groups[(r["src"], r["lat"], r["lng"])]
        if len(names) > 1:
            ok = {x["name"] for x in rows if x["src"] == r["src"] and (x["lat"], x["lng"]) == (r["lat"], r["lng"]) and confirmed(x)}
            if ok and r["name"] not in ok:
                continue
            if not confirmed(r) and any(o["src"] != r["src"] and o["name"] == r["name"] for o in rows):
                continue
        out.append(r)
    return out


def dist_m(la1: float, lo1: float, la2: float, lo2: float) -> float:
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


AGREE_M = 300.0   # 다른 출처의 같은 이름 역이 이 안에 있으면 '일치'


def source_scores(rows: list[dict]) -> dict[str, float]:
    """출처(src)별 신뢰도 = 같은 이름이 다른 출처에도 있는 점 중 AGREE_M 안에서 일치하는 비율.
    2026-10-14: 6호선 역위치 파일이 환승역마다 700m~1.2km 어긋났고, 서울교통공사 파일의 잠실새내는 1.8km 어긋났다."""
    by_name: dict[str, list[dict]] = {}
    for r in rows:
        by_name.setdefault(r["name"], []).append(r)
    hit: dict[str, int] = {}
    tot: dict[str, int] = {}
    for r in rows:
        others = [o for o in by_name[r["name"]] if o.get("src") != r.get("src")]
        if not others:
            continue
        src = r.get("src", "")
        tot[src] = tot.get(src, 0) + 1
        hit[src] = hit.get(src, 0) + any(dist_m(r["lat"], r["lng"], o["lat"], o["lng"]) <= AGREE_M for o in others)
    return {k: hit.get(k, 0) / v for k, v in tot.items()}


def merge_stations(rows: list[dict]) -> list[dict]:
    """같은 이름이 MERGE_M 안이면 한 역(노선 합침, 좌표 평균). 같은 이름이 CONFLICT_M 안에 따로 있으면(한쪽 좌표 오류)
    출처 신뢰도 합이 큰 쪽 좌표만 남기고 노선은 합친다. 멀면(양평 5호선 vs 경의중앙) 다른 역."""
    score = source_scores(rows)
    out: list[dict] = []
    for r in rows:
        hit = next((s for s in out if s["name"] == r["name"] and dist_m(s["lat"], s["lng"], r["lat"], r["lng"]) <= MERGE_M), None)
        src = r.get("src", "")
        if hit:
            if r["line"] and r["line"] not in hit["lines"]:
                hit["lines"].append(r["line"])
            n = hit["n"]
            hit["lat"], hit["lng"], hit["n"] = (hit["lat"] * n + r["lat"]) / (n + 1), (hit["lng"] * n + r["lng"]) / (n + 1), n + 1
            hit["w"] += score.get(src, 0.5)
        else:
            out.append({"name": r["name"], "lines": [r["line"]] if r["line"] else [], "lat": r["lat"], "lng": r["lng"], "n": 1,
                        "w": score.get(src, 0.5)})
    keep = []
    for s in sorted(out, key=lambda x: (-x["w"], -x["n"])):
        twin = next((k for k in keep if k["name"] == s["name"] and dist_m(k["lat"], k["lng"], s["lat"], s["lng"]) <= CONFLICT_M), None)
        if twin:
            twin["lines"] += [ln for ln in s["lines"] if ln not in twin["lines"]]
        else:
            keep.append(s)
    return drop_strays(keep)


STRAY_M = 5000   # 같은 노선 역이 이 안에 하나도 없으면 엉뚱한 곳에 찍힌 좌표


def drop_strays(stations: list[dict]) -> list[dict]:
    """같은 이름이 멀리 둘로 남은 역 중 원본 좌표가 틀린 쪽을 뺀다(2026-10-15: 수서 수인분당이 이천, 판교 신분당선이 수원,
    가정 인천2호선이 전북, 연신내 6호선이 태릉 쪽에 찍힌 파일). 틀린 쪽으로 보는 것:
    ① 같은 노선 역이 STRAY_M 안에 하나도 없는데 다른 쪽은 있다  ② 노선이 전부 다른 쪽(더 믿을 만한)에 이미 있다.
    뺀 쪽 노선은 남는 쪽에 합친다. 양평(5호선·경의중앙)처럼 둘 다 이웃 역이 있으면 다른 역으로 둔다."""
    def lonely(s):
        ls = set(s["lines"])
        return bool(ls) and not any(o is not s and set(o["lines"]) & ls and dist_m(s["lat"], s["lng"], o["lat"], o["lng"]) <= STRAY_M
                                    for o in stations)

    drop = set()
    by_name: dict[str, list[dict]] = {}
    for s in stations:
        by_name.setdefault(s["name"], []).append(s)
    for group in by_name.values():
        if len(group) < 2:
            continue
        alone = {id(s) for s in group if lonely(s)}
        if alone and len(alone) < len(group):
            drop |= alone
        ranked = sorted((s for s in group if id(s) not in drop), key=lambda s: (-s["w"], -s["n"], -len(s["lines"])))
        for i, s in enumerate(ranked):
            if any(set(s["lines"]) <= set(t["lines"]) for t in ranked[:i] if id(t) not in drop):
                drop.add(id(s))
        keep = [s for s in group if id(s) not in drop]
        for s in group:
            if id(s) in drop and keep:
                keep[0]["lines"] += [ln for ln in s["lines"] if ln not in keep[0]["lines"]]
    return [s for s in stations if id(s) not in drop]


def nearest(lat: float, lng: float, stations: list[dict]) -> tuple[dict | None, float | None]:
    best, bd = None, None
    for s in stations:
        if abs(s["lat"] - lat) > 0.05 or abs(s["lng"] - lng) > 0.06:   # 약 5km 밖은 건너뜀
            continue
        d = dist_m(lat, lng, s["lat"], s["lng"])
        if bd is None or d < bd:
            best, bd = s, d
    return best, (round(bd) if bd is not None else None)
