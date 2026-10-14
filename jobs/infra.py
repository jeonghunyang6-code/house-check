"""생활 인프라 수집·단지 연결 (collector/infra.py, 0025). 공공데이터포털 파일(collector/datagokr_file.py)을 받는다.

    python -m jobs.infra stations [--dir 내려받은_파일_폴더]   # 역 위치 → station, 단지별 가장 가까운 역
    python -m jobs.infra schoolzone                           # 초등학교 통학구역(SHP) → 단지별 배정 통학구역 (pyshp·pyproj·shapely)

좌표가 있는 단지(complexes.lat, jobs/geo.py)만 연결한다. 사이트가 자주 끊겨 파일마다 재시도하고, 보안문자를 요구하면 멈춘다.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from collections import Counter

from collector.datagokr_file import CaptchaRequired, DownloadError, download
from collector.db import Db, DbError, connect, lit, select
from collector import hira
from collector.infra import drop_shared_coords, merge_stations, nearest, normalize_station
from collector.neis import OFFICES, PAGE, NeisError, count_by_dong, fetch_page, match_dong
from collector.kapt import _get_json
from collector.regions import REGIONS
from collector.sources.molit import ApiError, QuotaExceeded

# 수도권 도시·광역철도 역 위치 (공공데이터포털 파일데이터 번호). 2026-10-14 확인한 것만.
# 국가철도공단·코레일의 일반열차역 목록(15067652·15127532)은 KTX·일반역 위주라 넣지 않는다
STATION_FILES = {
    "15099316": "",   # 서울교통공사 1~8호선 역사 좌표
    "15083751": "",   # 인천교통공사 1·2호선
    # 국가철도공단 노선별 역위치 (열: 철도운영기관, 선명, 역명, 경도, 위도)
    "15041300": "", "15041301": "", "15041302": "", "15041303": "", "15041304": "", "15041305": "", "15041306": "",
    "15041334": "", "15041335": "",                  # 8·9호선
    "15041324": "", "15041325": "", "15041326": "",  # 우이신설, 의정부경전철, 에버라인
    "15041331": "", "15041332": "",                  # 공항철도, 자기부상
    "15041333": "", "15041336": "", "15041337": "",  # 분당선, 수인선, 신분당선
    "15041338": "", "15041339": "",                  # 인천 1·2호선
    "15041486": "", "15041487": "",                  # 경강선, 경의중앙선
    "15041483": "",                                  # 경춘선 (2026-10-15 추가)
}
# 아직 못 받은 것: 15041308·15041309·15041328·15041485 는 2026-10-15 에도 페이지 오류(500). 서해선·김포골드라인·신림선·GTX-A 는
# 공공데이터포털에서 역위치 파일을 찾지 못함 → 해당 역 주변 단지는 거리가 길게 나올 수 있다
SCHOOL_ZONE_FILE = "15159265"   # 한국교육시설안전원 초등학교통학구역 (SHP, EPSG:5186)
MID_ZONE_FILE = "15159264"      # 같은 기관 중학교학교군 (SHP, EPSG:5186, 필드는 초등과 같음)
ZONE_SCHOOL_FILE = "15159266"   # 학교학구도연계정보 (CSV: 학구ID, 학교ID, 학교명, 학교급구분)
SCHOOL_POS_FILE = "15159184"    # 초중등학교위치 (CSV: 학교ID, 학교명, 학교급구분, 설립형태, 운영상태, 위도, 경도)
CAPITAL_SD = ("11", "28", "41")


def _decode(b: bytes) -> str:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("cp949", "replace")


def run_stations(db: Db, src_dir: str | None) -> int:
    rows, used = [], []
    for pk, line in STATION_FILES.items():
        path = os.path.join(src_dir, f"st_{pk}.csv") if src_dir else None
        try:
            data = open(path, "rb").read() if path and os.path.exists(path) else download(pk)[1]
        except CaptchaRequired as e:
            print(f"  {pk}: {e}", file=sys.stderr)
            return 2
        except DownloadError as e:
            print(f"  {pk}: 실패 {e}", file=sys.stderr)
            continue
        got = [dict(s, src=pk) for s in (normalize_station(r, line) for r in csv.DictReader(io.StringIO(_decode(data)))) if s]
        rows += got
        used.append(pk)
        print(f"  {pk}: 역 {len(got)}개", flush=True)
    st = merge_stations(drop_shared_coords(rows))
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    stmts = ["BEGIN;", "DELETE FROM station;"]
    for i in range(0, len(st), 500):
        stmts.append("INSERT INTO station (name, lines, lat, lng, sources) VALUES " + ", ".join(
            f"({lit(s['name'])}, {lit(', '.join(s['lines']))}, {lit(s['lat'])}, {lit(s['lng'])}, {lit(','.join(used))})" for s in st[i:i + 500]) + ";")
    vals = []
    for c in cx:
        s, d = nearest(float(c["lat"]), float(c["lng"]), st)
        if s:
            vals.append(f"({lit(c['apt_seq'])}, {lit(s['name'])}, {lit(', '.join(s['lines']))}, {d})")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET station_name = v.n, station_lines = v.l, station_m = v.d "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(s, n, l, d) WHERE c.apt_seq = v.s;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    near = sum(1 for v in vals if int(v.rsplit(", ", 1)[1].rstrip(")")) <= 700)
    print(f"  역 {len(st)}개(파일 {len(used)}개), 좌표 단지 {len(cx)}개 중 {len(vals)}개 연결, 700m 안 {near}개")
    return 0


def _load_zones(pk: str):
    """한국교육시설안전원 학구도 SHP → (zones[(id, 이름, 공동학구 여부 GB, 도형)], STRtree, 4326→5186 변환)."""
    import zipfile

    import shapefile
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.strtree import STRtree

    _, data = download(pk)
    z = zipfile.ZipFile(io.BytesIO(data))
    base = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                          shx=io.BytesIO(z.read(base + ".shx")), encoding="cp949")
    zones = [(sr.record["HAKGUDO_ID"], sr.record["HAKGUDO_NM"], str(sr.record["HAKGUDO_GB"]), shape(sr.shape.__geo_interface__))
             for sr in sf.shapeRecords() if str(sr.record["SD_CD"]) in CAPITAL_SD]
    tf = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)   # .prj: Korea 2000 중부원점(200000, 600000)
    return zones, STRtree([g for *_, g in zones]), tf


def _zone_hits(zones, tree, tf, lat: float, lng: float):
    from shapely.geometry import Point

    p = Point(*tf.transform(lng, lat))
    hits = [zones[i] for i in tree.query(p) if zones[i][3].contains(p)]
    return [h for h in hits if h[2] == "0"] or hits, hits


def run_schoolzone(db: Db) -> int:
    try:
        zones, tree, tf = _load_zones(SCHOOL_ZONE_FILE)
    except CaptchaRequired as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals, miss = [], 0
    for c in cx:
        main, hits = _zone_hits(zones, tree, tf, float(c["lat"]), float(c["lng"]))
        if not main:
            miss += 1
            continue
        vals.append(f"({lit(c['apt_seq'])}, {lit(main[0][0])}, {lit(main[0][1])}, {lit(any(h[2] == '1' for h in hits))})")
    stmts = ["BEGIN;"]
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET school_zone_id = v.i, school_zone = v.n, school_zone_shared = v.s "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, i, n, s) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  수도권 통학구역 {len(zones)}개, 좌표 단지 {len(cx)}개 중 {len(vals)}개 연결 (못 넣은 단지 {miss})")
    return 0


def _csv_file(pk: str) -> list[dict]:
    import zipfile

    _, data = download(pk)
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data))
        data = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv")))
    return list(csv.DictReader(io.StringIO(_decode(data))))


def run_midzone(db: Db) -> int:
    """단지가 든 중학교 학교군(서울은 여러 학교를 묶은 학교군, 경기·인천은 중학구가 많다)과
    그 학교군 안에서 직선으로 가장 가까운 중학교. 서울은 학교군 안 근거리 배정이 원칙이지만 실제 배정과 다를 수 있다."""
    try:
        zones, tree, tf = _load_zones(MID_ZONE_FILE)
        links = _csv_file(ZONE_SCHOOL_FILE)
        pos = _csv_file(SCHOOL_POS_FILE)
    except CaptchaRequired as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    schools = {}
    for r in pos:
        if r.get("학교급구분") != "중학교" or r.get("운영상태") != "운영":
            continue
        try:
            schools[r["학교ID"]] = {"id": r["학교ID"], "name": r["학교명"], "type": r.get("설립형태"),
                                   "lat": float(r["위도"]), "lng": float(r["경도"])}
        except (TypeError, ValueError):
            continue
    zone_ids = {z[0] for z in zones}
    in_zone: dict[str, list[dict]] = {}
    for r in links:
        if r.get("학구ID") in zone_ids and r.get("학교ID") in schools:
            in_zone.setdefault(r["학구ID"], []).append(schools[r["학교ID"]])
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals, miss = [], 0
    for c in cx:
        la, lo = float(c["lat"]), float(c["lng"])
        main, hits = _zone_hits(zones, tree, tf, la, lo)
        if not main:
            miss += 1
            continue
        cand = [s for h in hits for s in in_zone.get(h[0], [])]
        best, d = nearest(la, lo, cand) if cand else (None, None)
        vals.append(f"({lit(c['apt_seq'])}, {lit(main[0][0])}, {lit(main[0][1])}, {lit(any(h[2] == '1' for h in hits))}, "
                    f"{len({s['id'] for s in cand})}, {lit(best['id'] if best else None)}, {lit(best['name'] if best else None)}, "
                    f"{d if d is not None else 'NULL'}::int)")
    used = {s["id"] for v in in_zone.values() for s in v}
    stmts = ["BEGIN;", "DELETE FROM mid_school;"]
    rows = [s for s in schools.values() if s["id"] in used]
    for i in range(0, len(rows), 500):
        stmts.append("INSERT INTO mid_school (school_id, name, est_type, lat, lng, zone_ids) VALUES " + ", ".join(
            f"({lit(s['id'])}, {lit(s['name'])}, {lit(s['type'])}, {s['lat']}, {s['lng']}, "
            f"{lit(','.join(sorted(k for k, v in in_zone.items() if any(x['id'] == s['id'] for x in v))))})"
            for s in rows[i:i + 500]) + ";")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET mid_zone_id = v.zi, mid_zone = v.zn, mid_zone_shared = v.sh, mid_zone_schools = v.n, "
                     "mid_school_id = v.si, mid_school = v.sn, mid_school_m = v.d "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, zi, zn, sh, n, si, sn, d) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  수도권 중학교 학교군 {len(zones)}개, 중학교 {len(rows)}곳, 좌표 단지 {len(cx)}개 중 {len(vals)}개 연결 (못 넣은 단지 {miss})")
    return 0


def run_academy(db: Db) -> int:
    rows = []
    for office, name in OFFICES.items():
        total, page = None, 1
        while True:
            try:
                total, got = fetch_page(office, page)
            except NeisError as e:
                print(f"  {name} {page}쪽: {e}", file=sys.stderr)
                return 2
            rows += got
            if not got or page * PAGE >= total:
                break
            page += 1
            time.sleep(0.5)
        print(f"  {name}: {total}건", flush=True)
    counts, miss = count_by_dong(rows)
    cx = select(db, "SELECT apt_seq, region_code, umd_name FROM complexes")
    vals = []
    for c in cx:
        reg = REGIONS.get(c["region_code"] or "")
        if not reg:
            continue
        sido, sgg = reg.split(" ", 1)
        k = match_dong(counts, sido, sgg, c["umd_name"])
        if k:
            vals.append(f"({lit(c['apt_seq'])}, {counts[k]['exam']}, {counts[k]['exam_hagwon']})")
    today = time.strftime("%Y-%m-%d")
    items = list(counts.items())
    stmts = ["BEGIN;", "DELETE FROM academy_dong;"]
    for i in range(0, len(items), 1000):
        stmts.append("INSERT INTO academy_dong (sido, sgg, dong, n, exam, exam_hagwon, loaded_at) VALUES " + ", ".join(
            f"({lit(k[0])}, {lit(k[1])}, {lit(k[2])}, {v['n']}, {v['exam']}, {v['exam_hagwon']}, {lit(today)})"
            for k, v in items[i:i + 1000]) + ";")
    stmts.append("UPDATE complexes SET academy_exam = NULL, academy_hagwon = NULL;")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET academy_exam = v.e, academy_hagwon = v.h "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, e, h) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    opened = sum(v["n"] for v in counts.values())
    print(f"  받은 {len(rows)}건, 개원 {opened + miss}건 중 동 {len(counts)}개로 {opened}건 (동을 못 읽은 {miss}건), "
          f"단지 {len(cx)}개 중 {len(vals)}개 연결")
    return 0


def run_hospital(db: Db) -> int:
    pts = []
    for code, name in hira.SIDO.items():
        page, total = 1, 0
        while True:
            try:
                total, got = hira.items(_get_json(hira.URL, {"sidoCd": code, "pageNo": page, "numOfRows": hira.PAGE, "_type": "json"}))
            except (ApiError, QuotaExceeded) as e:
                print(f"  {name} {page}쪽: {e}", file=sys.stderr)
                return 2
            if page == 1 and got:
                print(f"  {name} 첫 행 필드: {sorted(got[0])}", flush=True)
            pts += [p for p in (hira.normalize(r) for r in got) if p]
            if not got or page * hira.PAGE >= total:
                break
            page += 1
        print(f"  {name}: {total}곳", flush=True)
    big = [p for p in pts if p["kind"] in hira.BIG]
    clinics = hira.Grid([p for p in pts if p["kind"] in hira.CLINIC])
    print(f"  종별: {sorted(Counter(p['kind'] + ' ' + p['kind_nm'] for p in pts).items())}")
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals = []
    for c in cx:
        la, lo = float(c["lat"]), float(c["lng"])
        h, d = nearest(la, lo, big)
        n = hira.count_within(clinics, la, lo, hira.CLINIC_M)
        vals.append(f"({lit(c['apt_seq'])}, {lit(h['name'] if h else None)}, {lit(h['kind_nm'] if h else None)}, "
                    f"{d if d is not None else 'NULL'}::int, {n})")
    stmts = ["BEGIN;", "DELETE FROM hospital;"]
    for i in range(0, len(big), 500):
        stmts.append("INSERT INTO hospital (name, kind, lat, lng) VALUES " + ", ".join(
            f"({lit(p['name'])}, {lit(p['kind_nm'])}, {p['lat']}, {p['lng']})" for p in big[i:i + 500]) + ";")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET hosp_name = v.n, hosp_kind = v.k, hosp_m = v.d, clinic_1km = v.c "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, n, k, d, c) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    near = sum(1 for v in vals if "NULL::int" not in v)
    print(f"  병원 {len(pts)}곳 중 종합병원급 {len(big)}곳, 좌표 단지 {len(cx)}개 중 5km 안 종합병원 있는 단지 {near}개")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stations", "schoolzone", "midzone", "academy", "hospital"])
    ap.add_argument("--dir", help="stations: 미리 받아 둔 st_<번호>.csv 폴더")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db = connect(a.db)
        rc = {"stations": lambda: run_stations(db, a.dir), "schoolzone": lambda: run_schoolzone(db),
              "midzone": lambda: run_midzone(db),
              "academy": lambda: run_academy(db), "hospital": lambda: run_hospital(db)}[a.mode]()
    except DbError as e:
        print(f"[infra] DB 오류: {e}", file=sys.stderr)
        rc = 1
    print(f"[infra] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
