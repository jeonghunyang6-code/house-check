"""단지 좌표 (collector/sgis.py, 0022). SGIS 는 이 클라우드 세션에서 막혀 있어 Actions(geo.yml)에서 돈다.

    python -m jobs.geo geocode --limit 5000   # 좌표 없는 단지 (최근 거래가 있는 단지 먼저)
    python -m jobs.geo boundary               # 수도권 행정동 경계 → adm_dong·adm_adjacent (0023), 원본은 HC_ARCHIVE 에
    python -m jobs.geo lifezone               # 서울 지역생활권(OA-15527) ↔ 행정동 → seoul_lifezone (0024). pyproj·pyshp·shapely 필요

주소 후보(지번 → 도로명 → K-apt 도로명)를 차례로 넣고, 돌아온 법정동이 우리 단지의 법정동과 맞을 때만 쓴다.
다 실패하면 geo_method = 'none' 으로 표시하고 다시 부르지 않는다(--retry-none 으로 다시).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import gzip
import json
import os

from collector.adjacency import adjacency, area_centroid, side_of
from collector.archive import open_store
from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sgis import Sgis, SgisError, accept, address_candidates

KST = ZoneInfo("Asia/Seoul")
FAIL_STREAK = 20


def run_geocode(db: Db, sg: Sgis, limit: int, retry_none: bool, today) -> int:
    cond = "c.geo_at IS NULL" + (" OR c.geo_method = 'none'" if retry_none else "")
    todo = select(db, f"""SELECT c.apt_seq, c.region_code, c.umd_name, c.jibun, c.road_addr, c.bjd_code, k.road_addr AS kapt_road
        FROM complexes c LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
        WHERE ({cond})
        ORDER BY EXISTS (SELECT 1 FROM deals d WHERE d.apt_seq = c.apt_seq) DESC, c.region_code, c.apt_seq LIMIT {int(limit)}""")
    batch: list[str] = []
    ok = miss = err = streak = 0
    by: dict[str, int] = {}

    def flush():
        if batch:
            db.query("BEGIN;\n" + "\n".join(batch) + "\nCOMMIT;")
            batch.clear()

    shown = 0
    for c in todo:
        hit, method, seen = None, "none", []
        try:
            rn = REGIONS.get(c["region_code"], "")
            for m, addr in address_candidates(rn, c["umd_name"], c["jibun"], c["road_addr"], c["kapt_road"]):
                h = sg.geocode(addr)
                seen.append((addr, h))
                if accept(h, c["bjd_code"], c["umd_name"], rn):
                    hit, method = h, m
                    break
            if not hit and shown < 5:   # 못 찾은 이유를 볼 수 있게 처음 5곳만 SGIS 답을 남긴다(2026-10-27 화성 읍면)
                shown += 1
                print(f"  못 찾음 {c['apt_seq']} 우리 동 '{c['umd_name']}' 법정동 {c['bjd_code']}: "
                      + " | ".join(f"{a_} → {({k: h_.get(k) for k in ('leg_cd', 'leg_nm', 'sgg_nm')} if h_ else None)}" for a_, h_ in seen))
        except SgisError as e:
            err += 1
            streak += 1
            print(f"  {c['apt_seq']}: 실패 {e}", file=sys.stderr)
            if streak >= FAIL_STREAK:
                flush()
                print(f"  실패가 {streak}번 연달아 이어져 중단 (좌표 {ok}개 받음)", file=sys.stderr)
                return 2
            continue
        streak = 0
        if hit:
            ok += 1
            by[method] = by.get(method, 0) + 1
            batch.append(f"UPDATE complexes SET lat = {lit(float(hit['y']))}, lng = {lit(float(hit['x']))}, adm_cd = {lit(hit.get('adm_cd'))}, "
                         f"adm_nm = {lit(hit.get('adm_nm'))}, geo_method = {lit(method)}, geo_at = {lit(today)} WHERE apt_seq = {lit(c['apt_seq'])};")
        else:
            miss += 1
            batch.append(f"UPDATE complexes SET geo_method = 'none', geo_at = {lit(today)} WHERE apt_seq = {lit(c['apt_seq'])};")
        if len(batch) >= 200:
            flush()
            print(f"  진행 {ok + miss}/{len(todo)}: 좌표 {ok} {by}, 못 찾음 {miss}, 실패 {err}")
    flush()
    left = select(db, "SELECT count(*) AS n FROM complexes WHERE geo_at IS NULL")[0]["n"]
    print(f"  좌표 {ok}개 {by}, 못 찾음 {miss}, 실패 {err}, 남은 단지 {left}개")
    return 1 if err else 0


SIDO = {"11": "서울", "23": "인천", "31": "경기"}   # SGIS 시도 코드
YEARS = ("2025", "2024", "2023")


def run_boundary(db: Db, sg: Sgis, archive: str | None) -> int:
    sggs = [r["cd"] for sd in SIDO for r in sg.stage(sd)]
    year = next((y for y in YEARS if sg.hadm_boundary(sggs[0], y)), None)
    if not year:
        print("  경계 연도를 찾지 못함", file=sys.stderr)
        return 1
    feats = []
    for cd in sggs:
        fs = sg.hadm_boundary(cd, year)
        for f in fs:
            p = f.get("properties") or {}
            feats.append({"adm_cd": str(p.get("adm_cd")), "adm_nm": p.get("adm_nm") or "", "geometry": f.get("geometry") or {}})
        print(f"  {cd}: 행정동 {len(fs)}개", flush=True)
    adj = adjacency(feats)
    rows = []
    for f in feats:
        a, cx, cy = area_centroid(f["geometry"])
        rows.append("(" + ", ".join(lit(v) for v in (f["adm_cd"], f["adm_nm"], year, round(a / 1e6, 4), round(cx, 1), round(cy, 1),
                                                      side_of(f["adm_nm"]))) + ")")
    stmts = ["BEGIN;", "DELETE FROM adm_adjacent;", "DELETE FROM adm_dong;"]
    for i in range(0, len(rows), 500):
        stmts.append("INSERT INTO adm_dong (adm_cd, adm_nm, year, area_km2, cx, cy, han_side) VALUES " + ", ".join(rows[i:i + 500]) + ";")
    for i in range(0, len(adj), 1000):
        stmts.append("INSERT INTO adm_adjacent (a, b, shared, cross_river) VALUES "
                     + ", ".join(f"({lit(a)}, {lit(b)}, {n}, {lit(r)})" for a, b, n, r in adj[i:i + 1000]) + ";")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    if archive:
        fc = {"type": "FeatureCollection", "crs": "EPSG:5179", "year": year,
              "features": [{"type": "Feature", "properties": {"adm_cd": f["adm_cd"], "adm_nm": f["adm_nm"]}, "geometry": f["geometry"]}
                           for f in feats]}
        open_store(archive).put(f"hadm_{year}.geojson.gz", gzip.compress(json.dumps(fc, ensure_ascii=False).encode()))
    river = sum(1 for *_, r in adj if r)
    print(f"  {year}년 경계: 행정동 {len(feats)}개, 인접 {len(adj)}쌍 (한강 건너 {river}쌍)")
    return 0


LIFEZONE_PAGE = "https://data.seoul.go.kr/dataList/OA-15527/S/1/datasetView.do"
LIFEZONE_FILE = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false"
LIFEZONE_CRS = ("EPSG:5186", "EPSG:5181", "EPSG:5174", "EPSG:2097", "EPSG:5179")   # 파일에 .prj 가 없어 맞는 것을 고른다


def run_lifezone(db: Db) -> int:
    """서울 열린데이터광장 생활권경계 shp(공개 파일 1개)를 받아 행정동 중심이 어느 지역생활권에 드는지 잇는다."""
    import io
    import re
    import urllib.parse
    import urllib.request
    import zipfile

    import shapefile                       # pyshp
    from pyproj import Transformer
    from shapely.geometry import Point, shape

    ua = {"User-Agent": "house-check (personal research)"}
    page = urllib.request.urlopen(urllib.request.Request(LIFEZONE_PAGE, headers=ua), timeout=60).read().decode("utf-8", "replace")
    seq = re.search(r"downloadFile\('(\d+)'\)", page).group(1)
    body = urllib.parse.urlencode({"infId": "OA-15527", "infSeq": seq, "seq": seq}).encode()
    data = urllib.request.urlopen(urllib.request.Request(LIFEZONE_FILE, data=body, headers=ua), timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    base = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                          shx=io.BytesIO(z.read(base + ".shx")), encoding="cp949")
    zones = []
    for sr in sf.shapeRecords():
        label = sr.record["LABEL"]                     # '지역생활권(강남구_대치도곡)', '권역생활권(동남권)'
        m = re.match(r"(지역|권역)생활권\((.+)\)", label or "")
        if m:
            zones.append((m.group(1), m.group(2), shape(sr.shape.__geo_interface__)))
    dongs = select(db, "SELECT adm_cd, cx, cy FROM adm_dong WHERE adm_cd LIKE '11%'")
    best = None
    for crs in LIFEZONE_CRS:                           # 서울 행정동 중심이 가장 많이 생활권 안에 드는 좌표계
        tf = Transformer.from_crs("EPSG:5179", crs, always_xy=True)
        pts = {d["adm_cd"]: Point(*tf.transform(d["cx"], d["cy"])) for d in dongs}
        hit = sum(1 for p in pts.values() if any(k == "지역" and g.contains(p) for k, _, g in zones))
        if not best or hit > best[1]:
            best = (crs, hit, pts)
    crs, hit, pts = best
    rows = []
    for cd, p in pts.items():
        local = next((n for k, n, g in zones if k == "지역" and g.contains(p)), None)
        area = next((n for k, n, g in zones if k == "권역" and g.contains(p)), None)
        if local:
            rows.append(f"({lit(cd)}, {lit(local)}, {lit(area)}, 'centroid')")
    db.query("BEGIN;\nDELETE FROM seoul_lifezone;\n" + (("INSERT INTO seoul_lifezone (adm_cd, local_zone, area_zone, method) VALUES "
                                                          + ", ".join(rows) + ";\n") if rows else "") + "COMMIT;")
    n_local = len({n for k, n, _ in zones if k == "지역"})
    print(f"  생활권 파일 좌표계 {crs}: 지역생활권 {n_local}개, 서울 행정동 {len(dongs)}개 중 {len(rows)}개 연결 (못 넣은 동 {len(dongs) - len(rows)})")
    return 0 if rows else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["geocode", "boundary", "lifezone"])
    ap.add_argument("--archive", default=os.environ.get("HC_ARCHIVE"), help="boundary: 경계 원본을 둘 곳 (gh | dir:경로)")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--retry-none", action="store_true")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        if a.mode == "boundary":
            rc = run_boundary(connect(a.db), Sgis(), a.archive)
        elif a.mode == "lifezone":
            rc = run_lifezone(connect(a.db))
        else:
            rc = run_geocode(connect(a.db), Sgis(), a.limit, a.retry_none, datetime.now(KST).date())
    except (DbError, SgisError) as e:
        print(f"[geo] 실패: {e}", file=sys.stderr)
        rc = 1
    print(f"[geo] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
