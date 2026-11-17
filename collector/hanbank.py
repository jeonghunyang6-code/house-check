"""한강변 단지 추정(입지 사실표 '한강', 2026-11-15 사용자 요청 A안): 한강 물가(강변)까지 거리 + 강변 '1열' 여부.

물가 = OpenStreetMap 한강 물 영역(natural=water, name=한강)의 경계선(외곽·섬 포함). Overpass API 로 받는다(이 세션에선 막혀 GitHub 자동 작업에서, 401·403·429 면 멈춤).
© OpenStreetMap contributors (ODbL). 저장소에는 계산 결과(단지별 숫자)만 남긴다.

1열 추정 = 단지 중심 → 가장 가까운 물가 점 사이에 다른 아파트 단지 중심이 없음(시선 폭 🔧 150m, 물가까지 🔧 800m 안).
한계: 단지 중심 한 점이라 큰 단지는 동마다 다르고, 아파트가 아닌 건물·높이·나무는 못 본다 → 화면에 '추정'. 관심 단지는 손 관리(collector/hanview.py)가 우선.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request

BBOX = (37.40, 126.60, 37.70, 127.35)   # 남, 서, 북, 동: 김포·고양 ~ 하남·남양주 팔당 아래
QUERY = f"""[out:json][timeout:180];
(relation["natural"="water"]["name"="한강"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
 way["natural"="water"]["name"="한강"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}););
out geom({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});"""
URLS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
NEAR_BANK = 800   # 🔧 m: 이보다 멀면 '앞이 트임'으로 보지 않음. 400 으로 시험하니 큰 단지(잠실 장미 1~3·원베일리·선사현대)는 중심이 강에서 멀어 빠짐(2026-11-15)
LAT = 150         # 🔧 m: 시선 폭(이 안에 다른 단지 중심이 있으면 가림)
KEEP = 2000       # m: 이보다 먼 단지는 거리도 안 남김
KX, KY = math.cos(math.radians(37.5)) * 111320, 110940


class Stop(RuntimeError):
    pass


def fetch(opener=urllib.request.urlopen) -> dict:
    last = None
    for u in URLS:
        req = urllib.request.Request(u, data=urllib.parse.urlencode({"data": QUERY}).encode(), headers={"User-Agent": "house-check/1.0"})
        try:
            with opener(req, timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Stop(f"Overpass HTTP {e.code}") from None
            last = e
        except OSError as e:
            last = e
    raise RuntimeError(f"Overpass 실패: {last}")


def xy(la: float, lo: float) -> tuple[float, float]:
    return lo * KX, la * KY


def segments(osm: dict) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Overpass 'out geom' → 물가 선분들(m 평면 좌표). 관계의 바깥·안쪽(섬) 경계, 단독 way 모두."""
    out = []
    lines = []
    for el in osm.get("elements", []):
        if el.get("type") == "relation":
            lines += [m.get("geometry") or [] for m in el.get("members", []) if m.get("type") == "way"]
        elif el.get("type") == "way":
            lines.append(el.get("geometry") or [])
    for g in lines:
        pts = [xy(p["lat"], p["lon"]) for p in g if p]
        out += list(zip(pts, pts[1:]))
    return out


def nearest(p: tuple[float, float], segs) -> tuple[float, tuple[float, float]]:
    x, y = p
    best = (float("inf"), p)
    for (ax, ay), (bx, by) in segs:
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L)) if L else 0.0
        fx, fy = ax + t * dx, ay + t * dy
        d = math.hypot(x - fx, y - fy)
        if d < best[0]:
            best = (d, (fx, fy))
    return best


def blockers(p, f, others) -> list[str]:
    """p → 물가 점 f 사이(시선 폭 LAT 안)에 있는 다른 단지 이름."""
    vx, vy = f[0] - p[0], f[1] - p[1]
    L = math.hypot(vx, vy)
    if L < 1:
        return []
    ux, uy = vx / L, vy / L
    out = []
    for name, q in others:
        qx, qy = q[0] - p[0], q[1] - p[1]
        along, side = qx * ux + qy * uy, abs(-qx * uy + qy * ux)
        if 0.1 * L < along < L and side < LAT:
            out.append(name)
    return out


CELL = 500.0


def grid(segs) -> dict[tuple[int, int], list]:
    g: dict[tuple[int, int], list] = {}
    for s in segs:
        for (x, y) in s:
            g.setdefault((int(x // CELL), int(y // CELL)), []).append(s)
    return g


def around(g, p, r: int = 5) -> list:
    cx, cy = int(p[0] // CELL), int(p[1] // CELL)
    return [s for i in range(-r, r + 1) for j in range(-r, r + 1) for s in g.get((cx + i, cy + j), ())]


def judge(complexes: list[dict], segs) -> dict[str, tuple[int, bool, str | None]]:
    """complexes: {apt_seq, apt_name, lat, lng} → {apt_seq: (물가까지 m, 1열 추정, 가리는 단지 하나)} (KEEP 안만)."""
    pts = [(c["apt_seq"], c["apt_name"], xy(float(c["lat"]), float(c["lng"]))) for c in complexes]
    g, near = grid(segs), []
    for seq, nm, p in pts:
        cand = around(g, p)
        if not cand:
            continue
        d, f = nearest(p, cand)
        if d <= KEEP:
            near.append((seq, nm, p, d, f))
    out = {}
    for seq, nm, p, d, f in near:
        b = blockers(p, f, [(n2, p2) for s2, n2, p2, *_ in near if s2 != seq]) if d <= NEAR_BANK else []
        out[seq] = (round(d), d <= NEAR_BANK and not b, b[0] if b else None)
    return out


# ---- 건물 단위(2026-11-17 사용자: 정확도 높이기) ----
# 단지 중심 한 점 대신 OSM 아파트 건물(building=apartments) 하나하나로 본다: 단지 건물 중 하나라도 물가까지 사이에
# 다른 단지(또는 단지에 안 묶인) 아파트 건물이 없으면 '앞이 트임'. 트리마제처럼 옆 작은 단지 중심 때문에 틀리던 것을 줄임.
# 건물 → 단지: 가장 가까운 단지 중심 🔧 300m 안. OSM 에 건물이 없는 단지는 예전처럼 중심 한 점으로.
BLD_QUERY = f"""[out:json][timeout:240];
way["building"="apartments"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out center;"""
ASSIGN = 300      # 🔧 m
BLD_NEAR = 500    # 🔧 m: 건물에서 물가까지 이 안이어야 '앞이 트임' 후보
BLD_LAT = 35      # 🔧 m: 건물 시선 폭(아파트 한 동 너비 정도)
BCELL = 200.0


def fetch_buildings(opener=urllib.request.urlopen) -> list[tuple[float, float]]:
    last = None
    for u in URLS:
        req = urllib.request.Request(u, data=urllib.parse.urlencode({"data": BLD_QUERY}).encode(), headers={"User-Agent": "house-check/1.0"})
        try:
            with opener(req, timeout=300) as r:
                d = json.load(r)
            return [xy(e["center"]["lat"], e["center"]["lon"]) for e in d.get("elements", []) if e.get("center")]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise Stop(f"Overpass HTTP {e.code}") from None
            last = e
        except OSError as e:
            last = e
    raise RuntimeError(f"Overpass 건물 실패: {last}")


def judge_buildings(complexes: list[dict], segs, blds: list[tuple[float, float]]) -> dict[str, tuple[int, bool, str | None]]:
    base = judge(complexes, segs)                      # 중심 한 점 결과(건물이 없는 단지에 그대로)
    pts = {c["apt_seq"]: (c["apt_name"], xy(float(c["lat"]), float(c["lng"]))) for c in complexes}
    near = {s for s in base}                           # 물가 KEEP 안 단지
    cg: dict[tuple[int, int], list[str]] = {}
    for s in near:
        p = pts[s][1]
        cg.setdefault((int(p[0] // 500), int(p[1] // 500)), []).append(s)
    sg = grid(segs)
    owner, bpos, bdist, bfoot = [], [], [], []
    for b in blds:
        cand = around(sg, b, 3)
        if not cand:
            continue
        d, f = nearest(b, cand)
        if d > KEEP:
            continue
        cx, cy = int(b[0] // 500), int(b[1] // 500)
        best, bd = None, ASSIGN
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for s in cg.get((cx + i, cy + j), ()):
                    q = pts[s][1]
                    dd = math.hypot(b[0] - q[0], b[1] - q[1])
                    if dd < bd:
                        best, bd = s, dd
        owner.append(best); bpos.append(b); bdist.append(d); bfoot.append(f)
    bg: dict[tuple[int, int], list[int]] = {}
    for k, b in enumerate(bpos):
        bg.setdefault((int(b[0] // BCELL), int(b[1] // BCELL)), []).append(k)

    def blocked_by(k: int) -> str | None:
        p, f = bpos[k], bfoot[k]
        vx, vy = f[0] - p[0], f[1] - p[1]
        L = math.hypot(vx, vy)
        if L < 1:
            return None
        ux, uy = vx / L, vy / L
        seen = set()
        for t in range(0, int(L // 100) + 2):
            x, y = p[0] + ux * min(t * 100, L), p[1] + uy * min(t * 100, L)
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    for m in bg.get((int(x // BCELL) + i, int(y // BCELL) + j), ()):
                        if m in seen or m == k or owner[m] == owner[k] and owner[k] is not None:
                            continue
                        seen.add(m)
                        qx, qy = bpos[m][0] - p[0], bpos[m][1] - p[1]
                        along, side = qx * ux + qy * uy, abs(-qx * uy + qy * ux)
                        if 0.05 * L < along < L and side < BLD_LAT:
                            return pts[owner[m]][0] if owner[m] else "다른 건물"
        return None

    out = dict(base)
    by: dict[str, list[int]] = {}
    for k, s in enumerate(owner):
        if s:
            by.setdefault(s, []).append(k)
    for s, ks in by.items():
        ks.sort(key=lambda k: bdist[k])
        dmin = round(bdist[ks[0]])
        front, blk = False, None
        for k in ks:
            if bdist[k] > BLD_NEAR:
                break
            b = blocked_by(k)
            if b is None:
                front = True
                break
            blk = blk or b
        out[s] = (dmin, front, None if front else (blk or base[s][2]))
    return out
