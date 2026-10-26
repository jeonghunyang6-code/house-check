"""생활 인프라 수집·단지 연결 (collector/infra.py, 0025). 공공데이터포털 파일(collector/datagokr_file.py)을 받는다.

    python -m jobs.infra stations [--dir 내려받은_파일_폴더]   # 역 위치 → station, 단지별 가장 가까운 역
    python -m jobs.infra schoolzone                           # 초등학교 통학구역(SHP) → 단지별 배정 통학구역 (pyshp·pyproj·shapely)
    python -m jobs.infra elem                                 # 초등학교 위치 → elem_school, 통학구역 → 배정 초등학교 (schoolzone 뒤에)
    python -m jobs.infra access [--dir 역간거리_파일_폴더]      # 업무지구 접근 H2 → station_access, complexes.h2_* (stations 뒤에)

좌표가 있는 단지(complexes.lat, jobs/geo.py)만 연결한다. 사이트가 자주 끊겨 파일마다 재시도하고, 보안문자를 요구하면 멈춘다.
"""

from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import sys
import time
from collections import Counter

from collector.datagokr_file import CaptchaRequired, DownloadError, download
from collector.db import Db, DbError, connect, lit, select
from collector import access as ac
from collector import hira, schoolinfo
from collector.lifezone import station_keys, station_key
from collector.infra import dist_m, drop_shared_coords, merge_stations, nearest, normalize_station
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
# 15041308·15041309·15041328·15041485 는 2026-10-15 에도 페이지 오류(500). 서해선·김포골드라인·신림선·GTX-A 는
# 공공데이터포털에 역위치 파일이 없어 st_kakao_*.csv 로 넣는다(run_stations)
# 국가철도공단 노선별 역간거리 (행 순서 = 역 순서). 2026-10-16 확인. 코레일 묶음(15081858)에 1호선 지선·경의중앙 등이 같이 있다
LINE_ORDER_FILES = ("15041460", "15041425", "15041423", "15041350", "15041348", "15041297", "15041340", "15041299", "15041298",
                    "15041296", "15041327", "15041295", "15041310", "15041284", "15041269", "15041074", "15081850", "15081852",
                    "15081853", "15081855", "15081856", "15081857", "15081858", "15081860")
H2_WALK_MAX_M = 2000            # 🔧 가장 가까운 역이 이보다 멀면 걸어서 가는 계산을 하지 않는다(버스는 모델에 없음)
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
    # 공공데이터에 없는 노선(신림선·김포골드라인·서해선·GTX-A)은 입지톡 커넥터(카카오 지도 지하철역)로 모은
    # st_kakao_*.csv(선명, 역명, 경도, 위도)를 같은 폴더에 두면 함께 넣는다. 카카오 데이터라 저장소에 올리지 않는다
    for path in sorted(glob.glob(os.path.join(src_dir, "st_kakao_*.csv"))) if src_dir else []:
        got = [dict(s, src="kakao") for s in (normalize_station(r) for r in csv.DictReader(open(path, encoding="utf-8"))) if s]
        rows += got
        used.append("kakao")
        print(f"  {os.path.basename(path)}: 역 {len(got)}개", flush=True)
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


def run_access(db: Db, src_dir: str | None) -> int:
    blocks = []
    for pk in LINE_ORDER_FILES:
        path = os.path.join(src_dir, f"{pk}.bin") if src_dir else None
        try:
            data = open(path, "rb").read() if path and os.path.exists(path) else download(pk)[1]
        except CaptchaRequired as e:
            print(f"  {pk}: {e}", file=sys.stderr)
            return 2
        except DownloadError as e:
            print(f"  {pk}: 실패 {e}", file=sys.stderr)
            continue
        blocks += ac.parse_line_file(ac.decode(data))
    st = station_keys(select(db, "SELECT name, lines, lat, lng FROM station"))
    for s in st.values():
        s["lines"] = {ac.canon_line(x) for x in s["lines"]}
    g = ac.build_graph(st, blocks)
    res = {c: ac.access(g, {k for k, s in st.items() if s["name"] in names}) for c, names in ac.CBD.items()}
    lost = [k for k in st if not any(k in res[c] for c in res)]
    today = time.strftime("%Y-%m-%d")

    def cell(c, k):
        v = res[c].get(k)
        return (f"{v[0]:.1f}", str(v[1])) if v else ("NULL", "NULL")
    stmts = ["BEGIN;", "DELETE FROM station_access;"]
    rows = [f"({lit(s['name'])}, {s['lat']}, {s['lng']}, " + ", ".join(", ".join(cell(c, k)) for c in ac.CBD) + f", {lit(today)})"
            for k, s in st.items()]
    for i in range(0, len(rows), 500):
        stmts.append("INSERT INTO station_access (name, lat, lng, cbd_min, cbd_tr, ybd_min, ybd_tr, gbd_min, gbd_tr, built) VALUES "
                     + ", ".join(rows[i:i + 500]) + ";")
    cx = select(db, "SELECT apt_seq, lat, lng, station_name, station_m FROM complexes WHERE station_name IS NOT NULL AND lat IS NOT NULL")
    vals = []
    for c in cx:
        if c["station_m"] is None or int(c["station_m"]) > H2_WALK_MAX_M:
            continue
        k = station_key(c["station_name"], float(c["lat"]), float(c["lng"]), st)
        walk = int(c["station_m"]) / ac.WALK_M_PER_MIN
        out = []
        for cb in ac.CBD:
            v = res[cb].get(k)
            out += [str(round(walk + v[0])), str(v[1])] if v else ["NULL", "NULL"]
        vals.append(f"({lit(c['apt_seq'])}, {', '.join(out)})")
    stmts.append("UPDATE complexes SET h2_cbd_min = NULL, h2_cbd_tr = NULL, h2_ybd_min = NULL, h2_ybd_tr = NULL, h2_gbd_min = NULL, h2_gbd_tr = NULL;")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET h2_cbd_min = v.a::int, h2_cbd_tr = v.b::smallint, h2_ybd_min = v.c::int, h2_ybd_tr = v.d::smallint, "
                     "h2_gbd_min = v.e::int, h2_gbd_tr = v.f::smallint "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(s, a, b, c, d, e, f) WHERE c.apt_seq = v.s;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  노선 {len(g)}개, 역 {len(st)}개 중 그래프 밖 {len(lost)}개 {lost[:10]}, 단지 {len(vals)}개(역 {H2_WALK_MAX_M}m 안)")
    for nm in ("잠실", "판교", "고덕", "녹번", "동탄", "상계"):
        k = next((k for k in st if st[k]["name"] == nm), None)
        if k:
            print(f"    {nm}: " + ", ".join(f"{c} {res[c][k][0]:.0f}분·환승{res[c][k][1]}" for c in ac.CBD if k in res[c]))
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


MID_NEAR = 3   # 학교군에 학교가 여럿이면 가까운 순으로 이만큼 보여준다 (배정 확정 아님)


def _schoolinfo_moves(schools: dict[str, dict], kind: str = "03") -> tuple[dict[str, dict], str | None]:
    """학구도 학교(kind 03 중·02 초) → 학교알리미 전·출입. 키가 없거나 실패하면 빈 값(학교군 연결은 그대로 한다)."""
    for year in (time.strftime("%Y"), str(int(time.strftime("%Y")) - 1)):
        try:
            base, moves = {}, {}
            for sgg in list(REGIONS) + schoolinfo.EXTRA_SGG:
                for r in schoolinfo.fetch(0, sgg, year, kind):
                    base[r["SCHUL_CODE"]] = r
                for r in schoolinfo.fetch(10, sgg, year, kind):
                    moves[r["SCHUL_CODE"]] = r
                time.sleep(0.3)
            base = list(base.values())
            if not moves:
                raise schoolinfo.SchoolInfoError("전출입 공시 없음")
        except schoolinfo.SchoolInfoError as e:
            print(f"  학교알리미 {year}: {e}", file=sys.stderr)
            continue
        linked = schoolinfo.match(schools, base)
        out = {}
        for sid, r in linked.items():
            m = moves.get(r["SCHUL_CODE"])
            if m:
                out[sid] = {"si_code": r["SCHUL_CODE"], "students": int(m.get("STDNT_SUM") or 0),
                            "mv_in": int(m.get("MVIN_SUM") or 0), "mv_out": int(m.get("MVT_SUM") or 0),
                            "net_in": schoolinfo.net_in_rate(m)}
        print(f"  학교알리미 {year} 공시({'초' if kind == '02' else '중'}): 기본정보 {len(base)}곳, 학구도 학교 {len(schools)}곳 중 {len(linked)}곳 연결, 전출입 {len(out)}곳")
        return out, year
    return {}, None


def run_midzone(db: Db) -> int:
    """단지가 든 중학교 학교군과 '배정 가능 학교들'. 학교군에 학교가 1곳이면 배정 확정, 여럿이면 학교군 안 거리·추첨
    배정이라 확정할 수 없어 가까운 순 MID_NEAR 곳과 학교군 평균을 보여준다(서울은 1곳짜리 학교군에 든 단지가 없다)."""
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
    used = {s["id"]: s for v in in_zone.values() for s in v}
    moves, year = _schoolinfo_moves(used)

    def zone_net_in(zid: str) -> float | None:
        ms = [moves[s["id"]] for s in in_zone.get(zid, []) if s["id"] in moves and moves[s["id"]]["students"] > 0]
        n = sum(m["students"] for m in ms)
        return round(sum(m["mv_in"] - m["mv_out"] for m in ms) / n * 100, 1) if n else None

    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals, miss, one = [], 0, 0
    for c in cx:
        la, lo = float(c["lat"]), float(c["lng"])
        main, hits = _zone_hits(zones, tree, tf, la, lo)
        if not main:
            miss += 1
            continue
        cand = list({s["id"]: s for h in hits for s in in_zone.get(h[0], [])}.values())
        one += len(cand) == 1
        ranked = sorted(cand, key=lambda s: dist_m(la, lo, s["lat"], s["lng"]))[:MID_NEAR]
        near = [{"id": s["id"], "name": s["name"], "m": round(dist_m(la, lo, s["lat"], s["lng"])),
                 "net_in": moves.get(s["id"], {}).get("net_in")} for s in ranked]
        vals.append(f"({lit(c['apt_seq'])}, {lit(main[0][0])}, {lit(main[0][1])}, {lit(any(h[2] == '1' for h in hits))}, "
                    f"{len(cand)}, {lit(len(cand) == 1)}, {lit(json.dumps(near, ensure_ascii=False))}::jsonb, "
                    f"{lit(zone_net_in(main[0][0]))}::numeric)")
    stmts = ["BEGIN;", "DELETE FROM mid_school;"]
    rows = list(used.values())
    for i in range(0, len(rows), 500):
        stmts.append("INSERT INTO mid_school (school_id, name, est_type, lat, lng, zone_ids, si_code, students, mv_in, mv_out, net_in, pban_yr) VALUES "
                     + ", ".join(
            f"({lit(s['id'])}, {lit(s['name'])}, {lit(s['type'])}, {s['lat']}, {s['lng']}, "
            f"{lit(','.join(sorted(k for k, v in in_zone.items() if any(x['id'] == s['id'] for x in v))))}, "
            + (lambda m: f"{lit(m.get('si_code'))}, {lit(m.get('students'))}::int, {lit(m.get('mv_in'))}::int, "
                         f"{lit(m.get('mv_out'))}::int, {lit(m.get('net_in'))}::numeric, {lit(year if m else None)})")(moves.get(s["id"], {}))
            for s in rows[i:i + 500]) + ";")
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET mid_zone_id = v.zi, mid_zone = v.zn, mid_zone_shared = v.sh, mid_zone_schools = v.n, "
                     "mid_assigned = v.one, mid_near = v.near, mid_zone_net_in = v.zni "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, zi, zn, sh, n, one, near, zni) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  수도권 중학교 학교군 {len(zones)}개, 중학교 {len(rows)}곳, 좌표 단지 {len(cx)}개 중 {len(vals)}개 연결 "
          f"(배정 확정 {one}, 못 넣은 단지 {miss})")
    return 0


CAPITAL_OFFICES = ("서울특별시교육청", "인천광역시교육청", "경기도교육청")
ELEM_NEAR = 3   # 통학구역에 학교가 여럿(공동통학구역 등)이면 가까운 순으로 이만큼


def elem_rows(pos: list[dict]) -> dict[str, dict]:
    out = {}
    for r in pos:
        if r.get("학교급구분") != "초등학교" or r.get("운영상태") != "운영" or r.get("시도교육청명") not in CAPITAL_OFFICES:
            continue
        try:
            out[r["학교ID"]] = {"id": r["학교ID"], "name": r["학교명"], "type": r.get("설립형태"), "lat": float(r["위도"]), "lng": float(r["경도"])}
        except (TypeError, ValueError):
            continue
    return out


def run_elem(db: Db) -> int:
    """초등학교 위치 → elem_school, 단지 통학구역(school_zone_id) → 배정 초등학교(complexes.elem_assigned). schoolzone 뒤에."""
    try:
        pos, links = _csv_file(SCHOOL_POS_FILE), _csv_file(ZONE_SCHOOL_FILE)
    except CaptchaRequired as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    schools = elem_rows(pos)
    in_zone: dict[str, list[dict]] = {}
    for r in links:
        if r.get("학교급구분") == "초등학교" and r.get("학교ID") in schools:
            in_zone.setdefault(r["학구ID"], []).append(schools[r["학교ID"]])
    cx = select(db, "SELECT apt_seq, lat, lng, school_zone_id FROM complexes WHERE lat IS NOT NULL AND school_zone_id IS NOT NULL")
    vals = []
    for c in cx:
        la, lo = float(c["lat"]), float(c["lng"])
        ranked = sorted(in_zone.get(c["school_zone_id"], []), key=lambda s: dist_m(la, lo, s["lat"], s["lng"]))[:ELEM_NEAR]
        if ranked:
            near = [{"id": s["id"], "name": s["name"], "m": round(dist_m(la, lo, s["lat"], s["lng"]))} for s in ranked]
            vals.append(f"({lit(c['apt_seq'])}, {lit(json.dumps(near, ensure_ascii=False))}::jsonb)")
    rows = list(schools.values())
    moves, year = _schoolinfo_moves(schools, kind="02")   # 0078 학생 수·1년 전입·전출(키 없으면 빈 값)
    mv = lambda s, k: lit(moves.get(s["id"], {}).get(k))
    stmts = ["BEGIN;", "DELETE FROM elem_school;"]
    for i in range(0, len(rows), 500):
        stmts.append("INSERT INTO elem_school (school_id, name, est_type, lat, lng, students, mv_in, mv_out, pban_yr) VALUES "
                     + ", ".join(f"({lit(s['id'])}, {lit(s['name'])}, {lit(s['type'])}, {s['lat']}, {s['lng']}, {mv(s, 'students')}::int, "
                                 f"{mv(s, 'mv_in')}::int, {mv(s, 'mv_out')}::int, {lit(year if s['id'] in moves else None)})" for s in rows[i:i + 500]) + ";")
    stmts.append("UPDATE complexes SET elem_assigned = NULL WHERE elem_assigned IS NOT NULL;")
    for i in range(0, len(vals), 1000):
        stmts.append(f"UPDATE complexes AS c SET elem_assigned = v.e FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, e) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  수도권 초등학교 {len(rows)}곳(전출입 {len(moves)}곳), 통학구역 있는 단지 {len(cx)}개 중 배정 학교 연결 {len(vals)}개")
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


CLOSED = ("폐점", "예정")   # 이름에 이 말이 있으면 문을 닫았거나 아직 안 연 곳


def run_mart(db: Db, path: str | None) -> int:
    """대형마트 TSV(place_id, 이름, 위도, 경도, 브랜드; 입지톡 커넥터로 모은 카카오 '대형마트 > 브랜드') → mart, 단지별 가장 가까운 곳."""
    if not path or not os.path.exists(path):
        print("  --file 로 대형마트 TSV 를 넘겨야 한다 (커넥터로 모은 것, 저장소에 두지 않음)", file=sys.stderr)
        return 2
    marts, seen = [], set()
    for line in open(path, encoding="utf-8"):
        pid, name, lat, lng, brand = line.rstrip("\n").split("\t")
        if pid in seen or any(w in name for w in CLOSED):
            continue
        seen.add(pid)
        marts.append({"id": pid, "name": name, "brand": brand, "lat": float(lat), "lng": float(lng)})
    today = time.strftime("%Y-%m-%d")
    cx = select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")
    vals = []
    for c in cx:
        m, d = nearest(float(c["lat"]), float(c["lng"]), marts)
        vals.append(f"({lit(c['apt_seq'])}, {lit(m['name'] if m else None)}, {d if d is not None else 'NULL'}::int)")
    stmts = ["BEGIN;", "DELETE FROM mart;",
             "INSERT INTO mart (place_id, name, brand, lat, lng, collected) VALUES " + ", ".join(
                 f"({lit(m['id'])}, {lit(m['name'])}, {lit(m['brand'])}, {m['lat']}, {m['lng']}, {lit(today)})" for m in marts) + ";"]
    for i in range(0, len(vals), 1000):
        stmts.append("UPDATE complexes AS c SET mart_name = v.n, mart_m = v.d "
                     f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(a, n, d) WHERE c.apt_seq = v.a;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    near = sum(1 for v in vals if "NULL::int" not in v)
    print(f"  대형마트 {len(marts)}곳, 좌표 단지 {len(cx)}개 중 5km 안 {near}개")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stations", "schoolzone", "midzone", "elem", "academy", "hospital", "mart", "access"])
    ap.add_argument("--dir", help="stations: 미리 받아 둔 st_<번호>.csv 폴더, access: <번호>.bin 역간거리 파일 폴더")
    ap.add_argument("--file", help="mart: 대형마트 TSV")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db = connect(a.db)
        rc = {"stations": lambda: run_stations(db, a.dir), "schoolzone": lambda: run_schoolzone(db),
              "midzone": lambda: run_midzone(db), "elem": lambda: run_elem(db),
              "academy": lambda: run_academy(db), "hospital": lambda: run_hospital(db), "mart": lambda: run_mart(db, a.file),
              "access": lambda: run_access(db, a.dir)}[a.mode]()
    except DbError as e:
        print(f"[infra] DB 오류: {e}", file=sys.stderr)
        rc = 1
    print(f"[infra] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
