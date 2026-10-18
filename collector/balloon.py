"""풍선효과 (viewpoints.md 규제 G2, 📖 규제 지역 밖 비슷한 급지로 수요 이동 → 따라가지 마라 p.288~292). jobs/balloon.py, 0044.

사건 = 시군구 전체에 토지거래허가(토허)가 새로 걸린 날(collector/policy.py ZONES). 그날 기준으로 수도권 시군구를
  inside   새로 규제된 곳
  adjacent 규제 밖이면서 규제 시군구(새로든 원래든)와 맞닿은 곳 (한강 건너 맞닿음 포함: 용산 ↔ 마포·동작 같은 곳)
  far      나머지 규제 밖
으로 나누고(사건 전부터 규제였던 곳은 뺀다), R-ONE 주간 매매지수의 기준 주 대비 누적 변화를 비교한다.
기준 주 = 효력일 전 마지막 조사 주(조사 기준일이 월요일). 2025-03·10 모두 발표가 효력 2~5일 전이라 기준 주는 발표 전이다.
수요 이동은 매입자 거주지(R-ONE 월간)로 본다: 외지인(다른 시군구 거주자)·서울 거주자 매수 비중, 사건 전 6개월 vs 다음 6개월.
작가는 '비슷한 급지'라고 했지만 여기서는 인접만 본다(급지로 더 나누면 표본이 너무 작다).
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from collector.policy import Zone

SIDO_SHORT = {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천"}
KS = (4, 13, 26, 52)
SHARE_MONTHS = 6


def name_region(adm_nm: str, regions: dict[str, str]) -> str | None:
    """'경기도 광주시 남종면' → '41610'. 시군구 이름이 하나로 정해질 때만(인천 옛 '서구' 같은 이름은 None)."""
    parts = adm_nm.split()
    if len(parts) < 3 or parts[0] not in SIDO_SHORT:
        return None
    sido, mid = SIDO_SHORT[parts[0]], parts[1:-1]
    for k in range(len(mid), 0, -1):
        hit = [c for c, n in regions.items() if n == " ".join([sido, *mid[:k]])]
        if len(hit) == 1:
            return hit[0]
    return None


def sgg_adjacency(pairs: list[tuple[str, str]], dong_region: dict[str, str]) -> dict[str, set[str]]:
    """행정동 인접 쌍 → 시군구 인접. 시군구를 모르는 동은 건너뛴다."""
    out: dict[str, set[str]] = {}
    for a, b in pairs:
        ra, rb = dong_region.get(a), dong_region.get(b)
        if ra and rb and ra != rb:
            out.setdefault(ra, set()).add(rb)
            out.setdefault(rb, set()).add(ra)
    return out


def _active(z: Zone, d: date) -> bool:
    return (z.start is None or z.start <= d) and (z.end is None or z.end >= d)


def events(zones: tuple[Zone, ...], since: date = date(2020, 1, 1)) -> list[tuple[date, set[str], set[str]]]:
    """[(효력일, 새로 규제된 시군구, 그날 규제 중인 시군구)] — 시군구 전체 토허만 본다."""
    sgg = [z for z in zones if z.kind == "토허" and z.scope == "sgg"]
    out = []
    for d in sorted({z.start for z in sgg if z.start and z.start >= since}):
        after = {c for z in sgg if _active(z, d) for c in z.region_codes}
        before = {c for z in sgg if _active(z, d - timedelta(days=1)) for c in z.region_codes}
        out.append((d, after - before, after))
    return out


def groups(newly: set[str], regulated: set[str], codes: set[str], adj: dict[str, set[str]]) -> dict[str, str]:
    out = {}
    for c in codes:
        if c in newly:
            out[c] = "inside"
        elif c in regulated:
            continue
        elif adj.get(c, set()) & regulated:
            out[c] = "adjacent"
        else:
            out[c] = "far"
    return out


def _at(series: list[tuple[date, float]], target: date) -> float | None:
    """target 주(또는 그 전 2주 안 가장 가까운 주)의 값. 추석처럼 발표 없는 주를 메운다."""
    cand = [v for d, v in series if target - timedelta(days=14) < d <= target]
    return cand[-1] if cand else None


def changes(series: list[tuple[date, float]], t0: date, until: date | None = None) -> dict | None:
    """until(다음 사건 효력일) 전까지만 본다: 다음 사건에서 붙은 바깥이 규제로 바뀌면 비교가 섞이기 때문."""
    s = sorted(x for x in series if until is None or x[0] < until)
    pre = [(d, v) for d, v in s if d < t0]
    if not pre or len(pre) == len(s):
        return None
    bd, bv = pre[-1]
    last_d, last_v = s[-1]
    out = {"base_date": bd, "weeks_now": (last_d - bd).days // 7, "chg_now": round((last_v / bv - 1) * 100, 2)}
    for k in KS:
        tgt = bd + timedelta(days=7 * k)
        v = _at(s, tgt) if tgt <= last_d else None
        out[f"chg_{k}w"] = round((v / bv - 1) * 100, 2) if v else None
    return out


def path(series: list[tuple[date, float]], t0: date, max_weeks: int = 52, until: date | None = None) -> dict[int, float]:
    s = sorted(x for x in series if until is None or x[0] < until)
    pre = [(d, v) for d, v in s if d < t0]
    if not pre:
        return {}
    bd, bv = pre[-1]
    out = {}
    for w in range(0, max_weeks + 1):
        tgt = bd + timedelta(days=7 * w)
        if tgt > s[-1][0]:
            break
        v = _at(s, tgt)
        if v:
            out[w] = (v / bv - 1) * 100
    return out


def group_path(paths: dict[str, dict[int, float]], grp: dict[str, str]) -> list[tuple[str, int, float, int]]:
    """[(grp, week, 중앙값, n)]"""
    out = []
    for g in ("inside", "adjacent", "far"):
        members = [paths[c] for c, gg in grp.items() if gg == g and c in paths]
        for w in sorted({w for p in members for w in p}):
            xs = [p[w] for p in members if w in p]
            if xs:
                out.append((g, w, round(median(xs), 2), len(xs)))
    return out


def _ym_add(ym: str, k: int) -> str:
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 + k, 12)
    return f"{y}{m + 1:02d}"


def shares(monthly: dict[str, dict], t0: date) -> dict:
    """monthly: YYYYMM → {total, same_sgg, seoul}. 사건 달은 빼고 앞 6개월, 뒤 6개월(있는 만큼)의 비중(%)."""
    ev = f"{t0.year}{t0.month:02d}"
    out = {}
    for tag, months in (("before", [_ym_add(ev, -k) for k in range(1, SHARE_MONTHS + 1)]),
                        ("after", [_ym_add(ev, k) for k in range(1, SHARE_MONTHS + 1)])):
        rows = [monthly[m] for m in months if m in monthly]
        tot = sum(r["total"] for r in rows)
        out[f"outsider_{tag}"] = round((tot - sum(r["same_sgg"] or 0 for r in rows)) * 100 / tot, 1) if tot else None
        out[f"seoul_{tag}"] = round(sum(r["seoul"] or 0 for r in rows) * 100 / tot, 1) if tot else None
    return out


def verdict(inside: float | None, adjacent: float | None, far: float | None, gap: float) -> str | None:
    """번짐 = 붙은 바깥이 먼 바깥보다 더 오름, 풍선 = 거기에 규제 지역보다도 더 오름 (🔧 gap %p)."""
    if inside is None or adjacent is None or far is None:
        return None
    if adjacent - far > gap and adjacent - inside > gap:
        return "풍선(바깥이 규제지역보다 더 오름)"
    if adjacent - far > gap:
        return "번짐(붙은 바깥도 오름)"
    return "번짐 없음"
