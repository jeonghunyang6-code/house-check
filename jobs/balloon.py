"""풍선효과 계산 (collector/balloon.py → balloon·balloon_path·market_signals.g2_balloon, 0044). rone.yml 이 매주 market 뒤에 돌린다.

    python -m jobs.balloon
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.balloon import KS, changes, events, group_path, groups, name_region, path, sgg_adjacency, shares, verdict
from collector.db import Db, DbError, connect, lit, select
from collector.policy import ZONES
from collector.regions import REGIONS

KST = ZoneInfo("Asia/Seoul")
GAP = 0.5   # 🔧 중앙값 차이 0.5%p 넘으면 '더 오름'


def adjacency(db: Db) -> dict[str, set[str]]:
    dong = {r["adm_cd"]: r["region_code"] for r in select(db, """
SELECT DISTINCT ON (adm_cd) adm_cd, region_code FROM complexes WHERE adm_cd IS NOT NULL
GROUP BY adm_cd, region_code ORDER BY adm_cd, count(*) DESC""")}
    for r in select(db, "SELECT adm_cd, adm_nm FROM adm_dong"):
        if r["adm_cd"] not in dong:
            rc = name_region(r["adm_nm"], REGIONS)
            if rc:
                dong[r["adm_cd"]] = rc
    return sgg_adjacency([(r["a"], r["b"]) for r in select(db, "SELECT a, b FROM adm_adjacent")], dong)


def series(db: Db) -> dict[str, list[tuple[date, float]]]:
    rows = select(db, """SELECT r.region_code AS rc, r.cls_id, w.week_date::text AS d, w.value AS v
FROM rone_weekly w JOIN rone_regions r USING (cls_id)
WHERE w.stat = 'sale' AND r.region_code IS NOT NULL AND w.week_date >= DATE '2024-06-01'""")
    by: dict[tuple[str, int], list[tuple[date, float]]] = {}
    for r in rows:
        by.setdefault((r["rc"], r["cls_id"]), []).append((date.fromisoformat(r["d"]), float(r["v"])))
    out: dict[str, list[tuple[date, float]]] = {}
    for (rc, _), s in sorted(by.items(), key=lambda kv: -len(kv[1])):   # 같은 시군구에 지역이 여럿이면 가장 긴 시계열
        out.setdefault(rc, sorted(s))
    return out


def buyers(db: Db) -> dict[str, dict[str, dict]]:
    """시군구 코드 하나에 딱 맞는 지역만 (경기 시 합계는 구가 따로 있으므로 뺀다)."""
    out: dict[str, dict[str, dict]] = {}
    for r in select(db, "SELECT period, region_codes, total, same_sgg, seoul FROM buyer_residence "
                        "WHERE region_codes IS NOT NULL AND position(',' IN region_codes) = 0 AND period >= '202401'"):
        out.setdefault(r["region_codes"], {})[r["period"]] = r
    return out


def run(db: Db, today: date) -> int:
    adj, ser, buy = adjacency(db), series(db), buyers(db)
    rows, paths_out, sig = [], [], None
    evs = events(ZONES)
    for i, (d, newly, regulated) in enumerate(evs):
        until = evs[i + 1][0] if i + 1 < len(evs) else None
        grp = groups(newly, regulated, set(ser), adj)
        paths = {}
        for c, g in grp.items():
            ch = changes(ser[c], d, until)
            if not ch:
                continue
            sh = shares(buy.get(c, {}), d)
            if c.startswith("11"):
                sh["seoul_before"] = sh["seoul_after"] = None   # 서울 지역은 '서울 거주자' 칸이 0
            rows.append(dict(event_date=d, region_code=c, grp=g, **ch, **sh))
            paths[c] = path(ser[c], d, until=until)
        paths_out += [(d, *x) for x in group_path(paths, grp)]
        cur = [r for r in rows if r["event_date"] == d]
        med = {g: _median([r["chg_now"] for r in cur if r["grp"] == g]) for g in ("inside", "adjacent", "far")}
        wk = max((r["weeks_now"] for r in cur), default=0)
        state = verdict(med["inside"], med["adjacent"], med["far"], GAP)
        if state and wk >= 4:
            adj_rows = [r for r in cur if r["grp"] == "adjacent" and r["seoul_before"] is not None and r["seoul_after"] is not None]
            sd = _median([r["seoul_after"] - r["seoul_before"] for r in adj_rows])
            sig = (round(med["adjacent"] - med["far"], 2), state,
                   f"{d:%Y.%m.%d} 토지거래허가 확대 뒤 {wk}주{'(다음 확대 전까지)' if until else ''}: 새로 규제된 곳 {med['inside']:+.2f}% · "
                   f"붙은 바깥 {med['adjacent']:+.2f}% · 먼 바깥 {med['far']:+.2f}% (R-ONE 주간 매매지수 중앙값)"
                   + (f". 붙은 바깥 서울 거주자 매수 비중 변화 중앙값 {sd:+.1f}%p(전후 6개월)" if sd is not None else "")
                   + f". 🔧 차이 {GAP}%p. 📖 규제 밖 비슷한 급지로 수요가 옮겨 가도 따라가지 마라 p.288~292")
    cols = ("event_date", "region_code", "grp", "base_date", *[f"chg_{k}w" for k in KS], "weeks_now", "chg_now",
            "outsider_before", "outsider_after", "seoul_before", "seoul_after")
    stmts = ["BEGIN;", "DELETE FROM balloon;", "DELETE FROM balloon_path;"]
    if rows:
        stmts.append(f"INSERT INTO balloon ({', '.join(cols)}) VALUES " + ", ".join("(" + ", ".join(lit(r.get(c)) for c in cols) + ")" for r in rows) + ";")
    if paths_out:
        stmts.append("INSERT INTO balloon_path (event_date, grp, week, median_chg, n) VALUES "
                     + ", ".join(f"({lit(d)}, {lit(g)}, {w}, {lit(m)}, {n})" for d, g, w, m, n in paths_out) + ";")
    if sig:
        stmts.append("INSERT INTO market_signals (key, asof, value, state, detail) VALUES ("
                     + ", ".join(lit(x) for x in ("g2_balloon", today, sig[0], sig[1], sig[2])) + ") ON CONFLICT (key) DO UPDATE SET "
                     "asof = EXCLUDED.asof, value = EXCLUDED.value, state = EXCLUDED.state, detail = EXCLUDED.detail;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    for d in sorted({r["event_date"] for r in rows}):
        n = {g: sum(1 for r in rows if r["event_date"] == d and r["grp"] == g) for g in ("inside", "adjacent", "far")}
        print(f"  {d}: 시군구 {n}")
    if sig:
        print(f"  신호: {sig[1]} ({sig[0]:+.2f}%p) — {sig[2]}")
    return 0


def _median(xs: list) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return round((xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2), 2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), datetime.now(KST).date())
    except DbError as e:
        print(f"[balloon] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
