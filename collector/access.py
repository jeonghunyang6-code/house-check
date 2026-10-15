"""업무지구 접근 H2 (순수 함수, jobs/access.py). 📖 교통은 중심업무지구(사대문·여의도·강남) 연결이 핵심, 어디서 내리는지 p.68~70, p.86~87.

노선 그래프: 국가철도공단 노선별 역간거리 파일의 행 순서 = 역 순서(같은 선명 안 앞뒤 행을 잇는다).
  파일마다 지선이 본선 뒤에 붙어 있어 순서만 믿으면 엉뚱한 역끼리 이어진다 → 앞뒤 행이라도 두 역 사이에 같은 노선 다른 역이
  끼어 있거나(BETWEEN) MAX_EDGE_M 보다 멀면 버리고, 노선이 끊기면 그 노선 역끼리 MAX_JOIN_M 안 가장 가까운 쌍으로 잇는다(지선 시작 역 → 분기역).
  파일이 없는 노선(신림선·김포골드라인 등)도 같은 방법으로 잇는다. GTX-A 는 SEQ 로 직접(서울역~수서 미개통).
시간: 구간 직선 거리 × DETOUR ÷ 노선 표정속도(정차 포함 평균 속도), 없으면 🔧 DEFAULT_KMH.
환승 🔧 TRANSFER_MIN, 역까지 걷기 📖 700m = 10분(p.220) → 70m/분. 버스·배차 대기는 넣지 않는다.
"""

from __future__ import annotations

import csv
import heapq
import io
import re
from collections import defaultdict

from collector.infra import dist_m, norm_name

MAX_EDGE_M = 15000       # 🔧 파일 앞뒤 역이라도 이보다 멀면 버린다 (공항철도 영종~청라 약 10km 는 살림)
BETWEEN = 1.15           # 🔧 a~c~b 거리 합이 a~b 의 1.15배 안인 같은 노선 역 c 가 있으면 a·b 는 이웃이 아니다 (하남검단산 → 둔촌동 같은 지선 경계)
SAME_SPOT_M = 300         # 같은 자리 역(옛 이름 당고개 = 불암산)은 '사이에 낀 역'으로 보지 않는다
MAX_JOIN_M = 6000        # 🔧 끊긴 조각 잇기 최대 거리
DETOUR = 1.15            # 🔧 선로 길이 ÷ 직선 거리
DEFAULT_KMH = 33.0       # 🔧 표정속도 자료 없는 노선: 서울교통공사 1~8호선 공식값의 중앙값(32.7~32.8)에 가깝게
LINE_KMH = {             # 1~8호선: 서울교통공사_1_8호선 표정속도 정보(2026-09-03, 공공데이터포털 15088952). 노선 안 구간이 여럿이면 본선 값
    "1호선": 26.0, "2호선": 32.5, "3호선": 34.0, "4호선": 40.1, "5호선": 32.8, "6호선": 29.0, "7호선": 32.3, "8호선": 36.0,
    "신분당선": 47.9,     # 나무위키(공식 자료 못 찾음, 2026-10-16)
    "수인분당": 37.07,    # 나무위키 왕십리~고색 일반(공식 자료 못 찾음, 2026-10-16)
}
# 파일에 없는 노선의 역 순서와 구간 총 시간(분). 시간은 거리 비례로 나눈다
SEQ = {"GTX-A": [(("운정중앙", "킨텍스", "대곡", "연신내", "서울"), 38.0),   # 운정중앙~서울역 약 38분, 수서~동탄 약 19~21분
                 (("수서", "성남", "구성", "동탄"), 20.0)]}             # (2026-10 운행 안내 정리 글). 서울역~수서는 미개통
TRANSFER_MIN = 5.0       # 🔧 환승 1회(걷기 + 기다림)
WALK_M_PER_MIN = 70.0    # 📖 역세권 700m = 걸어서 10분 p.220
# 🔧 업무지구 하차역 (작가는 지역 이름만 말함: 사대문·여의도·강남)
CBD = {
    "cbd": ("시청", "광화문", "종각", "을지로입구", "을지로3가", "종로3가"),
    "ybd": ("여의도", "여의나루", "국회의사당", "샛강"),
    "gbd": ("강남", "신논현", "역삼", "선릉", "삼성", "언주"),
}
ALIAS = {"신분당": "신분당선", "공항": "공항철도", "인천지하철1호선": "인천1호선", "인천지하철2호선": "인천2호선",
         "용인에버라인": "에버라인", "의정부경전철": "의정부", "경의중앙선": "경의중앙", "경춘선": "경춘", "경강선": "경강",
         "수인분당선": "수인분당", "우이신설선": "우이신설", "공항철도선": "공항철도"}


def canon_line(s: str) -> str:
    s = re.sub(r"\(.*?\)|\s", "", s or "")
    return ALIAS.get(s, s)


def parse_line_file(text: str) -> list[tuple[str, list[str]]]:
    """국가철도공단 역간거리 CSV → [(노선, [역명 순서])]. 같은 선명이 이어지는 행끼리 한 덩어리."""
    blocks: list[tuple[str, list[str]]] = []
    for r in csv.DictReader(io.StringIO(text)):
        line, name = canon_line(r.get("선명", "")), norm_name((r.get("역명") or "").strip())
        if not line or not name:
            continue
        if not blocks or blocks[-1][0] != line:
            blocks.append((line, []))
        if not blocks[-1][1] or blocks[-1][1][-1] != name:
            blocks[-1][1].append(name)
    return blocks


def decode(b: bytes) -> str:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def build_graph(stations: dict[str, dict], blocks: list[tuple[str, list[str]]]) -> dict[str, dict[str, list[tuple[str, float]]]]:
    """stations: 키 → {name, lat, lng, lines(set, canon)}. → 노선 → 역 키 → [(이웃 키, 분)]. 우리 역 표에 없는 노선의 파일 덩어리는 버린다."""
    by_name: dict[str, list[str]] = defaultdict(list)
    members: dict[str, set[str]] = defaultdict(set)
    for k, s in stations.items():
        by_name[s["name"]].append(k)
        for ln in s["lines"]:
            members[ln].add(k)

    def pick(name, line, prev):
        ks = [k for k in by_name.get(name, []) if line in stations[k]["lines"]]
        if len(ks) > 1 and prev:
            ks.sort(key=lambda k: _d(stations, k, prev))
        return ks[0] if ks else None

    def between(a, b, line):
        d = _d(stations, a, b)
        return any(_d(stations, a, c) + _d(stations, c, b) <= d * BETWEEN for c in members[line]
                   if c not in (a, b) and min(_d(stations, a, c), _d(stations, c, b)) > SAME_SPOT_M)

    edges: dict[str, set[tuple[str, str]]] = defaultdict(set)
    fixed: dict[tuple[str, str, str], float] = {}
    for line, names in blocks:
        if line not in members or line in SEQ:
            continue
        prev = None
        for nm in names:
            k = pick(nm, line, prev)
            if k is None:
                continue
            if prev and prev != k and _d(stations, prev, k) <= MAX_EDGE_M and not between(prev, k, line):
                edges[line].add(tuple(sorted((prev, k))))
            prev = k
    for line, segs in SEQ.items():
        for names, total in segs:
            ks = [pick(n, line, None) for n in names]
            if None in ks:
                continue
            ds = [_d(stations, a, b) for a, b in zip(ks, ks[1:])]
            for (a, b), d in zip(zip(ks, ks[1:]), ds):
                e = tuple(sorted((a, b)))
                edges[line].add(e)
                fixed[(line,) + e] = total * d / sum(ds)
    for line, ks in members.items():        # 끊긴 조각을 가장 가까운 쌍으로 잇기 (Kruskal, MAX_JOIN_M 안)
        if line in SEQ:
            continue
        comp = {k: k for k in ks}

        def find(x):
            while comp[x] != x:
                comp[x] = comp[comp[x]]
                x = comp[x]
            return x
        for a, b in edges[line]:
            comp[find(a)] = find(b)
        for d, a, b in sorted((_d(stations, a, b), a, b) for a in ks for b in ks if a < b):
            if d > MAX_JOIN_M:
                break
            if find(a) != find(b):
                comp[find(a)] = find(b)
                edges[line].add((a, b))
    g: dict[str, dict[str, list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
    for line, es in edges.items():
        for a, b in es:
            t = fixed.get((line, a, b)) or _d(stations, a, b) * DETOUR / 1000 / LINE_KMH.get(line, DEFAULT_KMH) * 60
            g[line][a].append((b, t))
            g[line][b].append((a, t))
    return g


def _d(st, a, b):
    return dist_m(st[a]["lat"], st[a]["lng"], st[b]["lat"], st[b]["lng"])


def access(g: dict[str, dict[str, list[tuple[str, float]]]], targets: set[str]) -> dict[str, tuple[float, int]]:
    """모든 역 → 목표 역 묶음 중 가장 빠른 곳까지 (분, 환승 수). 상태 = (역, 노선), 같은 역에서 노선 바꾸면 TRANSFER_MIN."""
    lines_at: dict[str, list[str]] = defaultdict(list)
    for line, adj in g.items():
        for k in adj:
            lines_at[k].append(line)
    best: dict[tuple[str, str], tuple[float, int]] = {}
    pq = []
    for k in targets:
        for ln in lines_at.get(k, []):
            best[(k, ln)] = (0.0, 0)
            heapq.heappush(pq, (0.0, 0, k, ln))
    while pq:
        t, tr, k, ln = heapq.heappop(pq)
        if best.get((k, ln), (1e18, 0)) < (t, tr):
            continue
        nxt = [(o, ln, t + dt, tr) for o, dt in g[ln][k]] + [(k, l2, t + TRANSFER_MIN, tr + 1) for l2 in lines_at[k] if l2 != ln]
        for o, l2, t2, tr2 in nxt:
            if (t2, tr2) < best.get((o, l2), (1e18, 0)):
                best[(o, l2)] = (t2, tr2)
                heapq.heappush(pq, (t2, tr2, o, l2))
    out: dict[str, tuple[float, int]] = {}
    for (k, _), v in best.items():
        if k not in out or v < out[k]:
            out[k] = v
    return out
