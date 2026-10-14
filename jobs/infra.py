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

from collector.datagokr_file import CaptchaRequired, DownloadError, download
from collector.db import Db, DbError, connect, lit, select
from collector.infra import drop_shared_coords, merge_stations, nearest, normalize_station

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


def run_schoolzone(db: Db) -> int:
    import zipfile

    import shapefile
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    try:
        _, data = download(SCHOOL_ZONE_FILE)
    except CaptchaRequired as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    z = zipfile.ZipFile(io.BytesIO(data))
    base = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                          shx=io.BytesIO(z.read(base + ".shx")), encoding="cp949")
    zones = [(sr.record["HAKGUDO_ID"], sr.record["HAKGUDO_NM"], str(sr.record["HAKGUDO_GB"]), shape(sr.shape.__geo_interface__))
             for sr in sf.shapeRecords() if str(sr.record["SD_CD"]) in CAPITAL_SD]
    tree = STRtree([g for *_, g in zones])
    tf = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)   # .prj: Korea 2000 중부원점(200000, 600000)
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals, miss = [], 0
    for c in cx:
        p = Point(*tf.transform(float(c["lng"]), float(c["lat"])))
        hits = [zones[i] for i in tree.query(p) if zones[i][3].contains(p)]
        main = [h for h in hits if h[2] == "0"] or hits
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stations", "schoolzone"])
    ap.add_argument("--dir", help="stations: 미리 받아 둔 st_<번호>.csv 폴더")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db = connect(a.db)
        rc = run_stations(db, a.dir) if a.mode == "stations" else run_schoolzone(db)
    except DbError as e:
        print(f"[infra] DB 오류: {e}", file=sys.stderr)
        rc = 1
    print(f"[infra] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
