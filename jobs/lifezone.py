"""생활권 묶음 E0 → lifezone, complexes.lifezone_id (0030). 방식은 collector/lifezone.py.

    python -m jobs.lifezone [--hist-dir DIR]

가격: 2020-01~ 매매. 2024-09 이전은 Releases raw-data 의 deals_hist_<시군구>.csv.gz(--hist-dir 에 받아 두거나, 없으면 내려받음),
그 뒤는 DB deals. 단지·분기별 ㎡당 중앙가(해제 제외, 20㎡ 이상).
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from statistics import mean, median

from collector import lifezone as lz
from collector.db import Db, DbError, connect, lit, select

RELEASE_API = "https://api.github.com/repos/jeonghunyang6-code/house-check/releases/tags/raw-data"


def _quarter(ym: str) -> str:
    return f"{ym[:4]}Q{(int(ym[4:6]) - 1) // 3 + 1}"


def _hist_files(hist_dir: str | None) -> list[str]:
    if hist_dir and glob.glob(os.path.join(hist_dir, "deals_hist_*.csv.gz")):
        return sorted(glob.glob(os.path.join(hist_dir, "deals_hist_*.csv.gz")))
    out_dir = hist_dir or "data/raw/hist"
    os.makedirs(out_dir, exist_ok=True)
    with urllib.request.urlopen(RELEASE_API, timeout=60) as r:
        assets = [a for a in json.load(r)["assets"] if a["name"].startswith("deals_hist_")]
    for a in assets:
        urllib.request.urlretrieve(a["browser_download_url"], os.path.join(out_dir, a["name"]))
    return sorted(glob.glob(os.path.join(out_dir, "deals_hist_*.csv.gz")))


def complex_prices(db: Db, hist_dir: str | None) -> dict[str, dict[str, float]]:
    vals: dict[tuple[str, str], list[float]] = defaultdict(list)
    for f in _hist_files(hist_dir):
        for r in csv.DictReader(gzip.open(f, "rt", encoding="utf-8")):
            if r["is_cancelled"] == "1" or not r["area_m2"] or not r["price_10k"] or float(r["area_m2"]) < 20:
                continue
            vals[(r["apt_seq"], _quarter(r["contract_month"]))].append(float(r["price_10k"]) / float(r["area_m2"]))
    out: dict[str, dict[str, tuple[float, int]]] = defaultdict(dict)
    for (k, q), v in vals.items():
        out[k][q] = (median(v), len(v))
    rows = select(db, """SELECT apt_seq, substr(contract_month,1,4)||'Q'||((substr(contract_month,5,2)::int-1)/3+1) AS q,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k/area_m2) AS p, count(*) AS n
        FROM deals WHERE NOT coalesce(is_cancelled, false) AND area_m2 >= 20 GROUP BY 1, 2""")
    for r in rows:
        old = out[r["apt_seq"]].get(r["q"])
        if old is None or int(r["n"]) > old[1]:          # 겹치는 분기는 거래 많은 쪽
            out[r["apt_seq"]][r["q"]] = (float(r["p"]), int(r["n"]))
    return {k: {q: p for q, (p, _) in qs.items()} for k, qs in out.items()}


def run(db: Db, hist_dir: str | None) -> int:
    cx = select(db, "SELECT apt_seq, region_code, lat, lng, adm_cd, station_name, station_m FROM complexes WHERE lat IS NOT NULL")
    stations = {r["name"]: {"lat": float(r["lat"]), "lng": float(r["lng"]),
                            "lines": {x.strip() for x in (r["lines"] or "").split(",") if x.strip()}}
                for r in select(db, "SELECT name, lines, lat, lng FROM station")}
    side = {r["adm_cd"]: r["han_side"] for r in select(db, "SELECT adm_cd, han_side FROM adm_dong")}
    adm_nm = {r["adm_cd"]: r["adm_nm"] for r in select(db, "SELECT adm_cd, adm_nm FROM adm_dong")}
    adj = [(r["a"], r["b"]) for r in select(db, "SELECT a, b FROM adm_adjacent WHERE NOT cross_river")]
    seoul = {r["adm_cd"]: r["local_zone"] for r in select(db, "SELECT adm_cd, local_zone FROM seoul_lifezone")}

    unit = {}
    for c in cx:
        u = lz.unit_of(c["station_name"], c["station_m"], c["adm_cd"])
        if u:
            unit[c["apt_seq"]] = u
    members: dict[str, list[dict]] = defaultdict(list)
    cxd = {c["apt_seq"]: c for c in cx}
    for k, u in unit.items():
        members[u].append(cxd[k])
    units = {}
    for u, cs in members.items():
        adms = Counter(c["adm_cd"] for c in cs if c["adm_cd"])
        units[u] = {"adms": adms, "side": lz.majority(Counter(side[a] for a in adms.elements() if side.get(a))),
                    "n": len(cs), "lat": mean(float(c["lat"]) for c in cs), "lng": mean(float(c["lng"]) for c in cs)}

    t0 = time.monotonic()
    ix = lz.unit_index(complex_prices(db, hist_dir), unit)
    print(f"  가격 지수: 단위 {len(units)}개 중 {len(ix)}개 ({time.monotonic() - t0:.0f}s)", flush=True)
    pairs = lz.candidate_pairs(units, stations, adj)
    scored = [(cv, a, b) for a, b in pairs if (cv := lz.ratio_cv(ix.get(a, {}), ix.get(b, {}))) is not None]
    groups = lz.merge(units, scored)

    by_root: dict[str, list[str]] = defaultdict(list)
    for u, r in groups.items():
        by_root[r].append(u)
    n = {u: units[u]["n"] for u in units}
    zid = {r: f"Z{i:04d}" for i, r in enumerate(sorted(by_root, key=lambda r: (-sum(n[u] for u in by_root[r]), r)), 1)}
    zones = [(zid[r], lz.zone_name(us, n, adm_nm), us) for r, us in by_root.items()]

    zone_of = {k: zid[groups[u]] for k, u in unit.items()}
    p, r, f = lz.pair_f1(zone_of, {k: seoul[c["adm_cd"]] for k, c in cxd.items() if seoul.get(c["adm_cd"])},
                         {k: c["region_code"] for k, c in cxd.items()})
    sizes = Counter(len(us) for _, _, us in zones)

    today = time.strftime("%Y-%m-%d")
    stmts = ["BEGIN;", "DELETE FROM lifezone;"]
    for i in range(0, len(zones), 500):
        stmts.append("INSERT INTO lifezone (zone_id, name, units, n_complex, built) VALUES " + ", ".join(
            f"({lit(z)}, {lit(nm)}, {lit(','.join(sorted(us)))}, {sum(n[u] for u in us)}, {lit(today)})" for z, nm, us in zones[i:i + 500]) + ";")
    zname = {z: nm for z, nm, _ in zones}
    vals = [f"({lit(k)}, {lit(z)}, {lit(zname[z])})" for k, z in zone_of.items()]
    stmts.append("UPDATE complexes SET lifezone_id = NULL, lifezone_name = NULL;")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET lifezone_id = v.z, lifezone_name = v.n "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, z, n) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  생활권 {len(zones)}개(단위 수별 {sorted(sizes.items())}), 단지 {len(zone_of)}개 연결. "
          f"후보 쌍 {len(pairs)}, 가격 비교 {len(scored)}. 서울 지역생활권 일치 P{p:.2f} R{r:.2f} F{f:.2f}")
    for s in ("녹번", "홍제", "무악재", "잠실", "대치", "고덕"):
        z = zone_of.get(next((k for k, u in unit.items() if u == "S:" + s), ""), None)
        if z:
            print(f"    {s} → {zname[z]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist-dir", help="deals_hist_*.csv.gz 폴더 (없으면 Releases 에서 받음)")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run(connect(a.db), a.hist_dir)
    except DbError as e:
        print(f"[lifezone] DB 오류: {e}", file=sys.stderr)
        rc = 1
    print(f"[lifezone] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
