"""H5 정비사업 단계 (collector/redev.py → redev_zone·complex_redev, 0055). 서울은 SEOUL_API_KEY 가 필요해 Actions(redev.yml)에서 돈다.
경기는 사용자가 PC 에서 받은 경기데이터드림 CSV 를 넣는다(collector/redev_gg.py, 0065). 서로의 행(src)은 지우지 않는다.

    python -m jobs.redev            # 서울을 받아서 덮어쓰고 단지 연결
    python -m jobs.redev --link-only   # DB 의 redev_zone 으로 단지 연결만 (클라우드 세션용)
    python -m jobs.redev --gg-file 경기_정비사업.csv   # 경기를 덮어쓰고 단지 연결
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.redev import DONE, FIELDS, REBUILD, general_sale, link, zone_row
from collector.regions import REGIONS

KST = ZoneInfo("Asia/Seoul")
COLS = (*FIELDS.values(), "region_code", "umd_name", "bun", "ji", "stage_no")
# 매주 다시 받을 때 좌표(jobs/redev_geo.py, 0074)는 구역 번호로 옮겨 둔다. 안 그러면 Geocoding 을 매주 다시 부른다
KEEP_GEO = "CREATE TEMP TABLE _geo ON COMMIT DROP AS SELECT code, lat, lng, geo_src FROM redev_zone WHERE src = '{}' AND geo_src IS NOT NULL;"
PUT_GEO = "UPDATE redev_zone z SET lat = g.lat, lng = g.lng, geo_src = g.geo_src FROM _geo g WHERE z.code = g.code;"


def log_stages(db: Db, today) -> None:
    """구역마다 지금 단계를 이력(0077)에 쌓는다. 표가 비어 있으면(처음) 알림 안 할 기준선으로 notified = true."""
    first = not select(db, "SELECT 1 FROM redev_stage_hist LIMIT 1")
    db.query(f"INSERT INTO redev_stage_hist (code, stage, stage_no, first_seen, notified) SELECT code, stage, stage_no, {lit(today)}, {lit(first)} "
             "FROM redev_zone WHERE stage IS NOT NULL ON CONFLICT (code, stage) DO NOTHING;")


def load(db: Db, today) -> int:
    from collector.redev import fetch_all
    zones = [zone_row(r, REGIONS) for r in fetch_all()]
    if not zones:
        print("  서울 정비사업: 0건", file=sys.stderr)
        return 1
    vals = ", ".join("(" + ", ".join([*(lit(z[c]) for c in COLS), lit(today)]) + ")" for z in zones)
    db.query(f"BEGIN;\n{KEEP_GEO.format('seoul')}\nDELETE FROM redev_zone WHERE src = 'seoul';\n"
             f"INSERT INTO redev_zone ({', '.join(COLS)}, fetched_at) VALUES {vals};\n{PUT_GEO}\nCOMMIT;")
    st = Counter(z["stage"] for z in zones)
    print(f"  서울 정비사업 {len(zones)}개 구역, 단계 {dict(st.most_common())}, 지번 못 읽음 {sum(z['umd_name'] is None for z in zones)}")
    return 0


GG_COLS = (*COLS, "src", "vl_old", "vl_new", "old_built", "member_hh", "gen_hh")


def load_gg(db: Db, path: str, today) -> int:
    from collector import redev_gg as G
    zones, dup = {}, 0
    for r in G.read(open(path, "rb").read()):
        z = G.zone_row(r)
        if z["code"] in zones:          # 2026-10-20 파일에 똑같은 행이 18개 두 번씩 있었다
            dup += 1
            if zones[z["code"]] != z:
                z["code"] += f"-{dup}"
            else:
                continue
        zones[z["code"]] = z
    cx_umd = select(db, "SELECT DISTINCT region_code, umd_name FROM complexes WHERE region_code LIKE '41%'")
    umd = {(r["region_code"], r["umd_name"]): r["region_code"] for r in cx_umd}
    for z in zones.values():
        z["umd_name"] = G.full_umd(z, REGIONS, cx_umd)
        z["region_code"] = G.region_code(z, REGIONS, umd)
    zs = list(zones.values())
    vals = ", ".join("(" + ", ".join([*(lit(z[c]) for c in GG_COLS), lit(today)]) + ")" for z in zs)
    db.query(f"BEGIN;\n{KEEP_GEO.format('gg')}\nDELETE FROM redev_zone WHERE src = 'gg';\n"
             f"INSERT INTO redev_zone ({', '.join(GG_COLS)}, fetched_at) VALUES {vals};\n{PUT_GEO}\nCOMMIT;")
    st = Counter(z["stage"] for z in zs)
    print(f"  경기 정비사업 {len(zs)}개 구역(같은 행 {dup}개 뺌), 단계 {dict(st.most_common())}, "
          f"지번 못 읽음 {sum(z['bun'] is None for z in zs)}, 시군구 못 정함 {sum(z['region_code'] is None for z in zs)}")
    return 0


def run_link(db: Db) -> int:
    zones = select(db, "SELECT code, region_code, zone_nm, biz_type, umd_name, bun, ji, existing_hh, sale_hh, gen_hh, stage_no, "
                   "zone_ymd, committee_ymd, assoc_ymd, impl_ymd, mgmt_ymd, construction_ymd FROM redev_zone")
    cx = select(db, "SELECT apt_seq, apt_name, region_code, umd_name, jibun, build_year FROM complexes WHERE region_code LIKE '11%' OR region_code LIKE '41%'")
    pairs = link(zones, cx)
    gen = general_sale(zones)
    stmts = ["BEGIN;", "DELETE FROM complex_redev;", "UPDATE redev_zone SET gen_sale_est = NULL, gen_ratio = NULL, gen_pct = NULL;"]
    if gen:
        stmts.append("UPDATE redev_zone z SET gen_sale_est = v.g, gen_ratio = v.r, gen_pct = v.p FROM (VALUES "
                     + ", ".join(f"({lit(c)}, {g}, {r}, {p})" for c, (g, r, p) in gen.items()) + ") AS v(c, g, r, p) WHERE z.code = v.c;")
    if pairs:
        stmts.append("INSERT INTO complex_redev (apt_seq, code, how) VALUES " + ", ".join(f"({lit(a)}, {lit(c)}, {lit(h)})" for a, c, h in pairs)
                     + " ON CONFLICT DO NOTHING;")
    db.query("\n".join([*stmts, "COMMIT;"]))
    n_reb = sum(1 for z in zones if z["biz_type"] in REBUILD and z.get("stage_no") != DONE)
    print(f"  일반분양 근사 {len(gen)}곳 (÷기존 세대 중앙값 {sorted(r for _, r, _ in gen.values())[len(gen) // 2] if gen else '-'})")
    print(f"  재건축 구역 {n_reb}곳 중 {len({c for _, c, _ in pairs})}곳이 단지 {len({a for a, _, _ in pairs})}곳과 연결 "
          f"({dict(Counter(h for _, _, h in pairs))})")
    return 0


MOLIT_FILE = "15160169"   # 국토교통부 전국 도시정비사업 통합 데이터(CSV, 연 1회)


def load_molit(db: Db) -> int:
    """경기 구역 단계를 국토부 전국 자료로 올린다(앞선 단계일 때만, collector/redev_molit.py). 2026-10-26 사용자 결정: 경기 파일 손으로 넣기 대신."""
    from collector import redev_molit as M
    from jobs.infra import _csv_file
    rows = [r for r in _csv_file(MOLIT_FILE) if r.get("시도") == "경기도"]
    zones = select(db, "SELECT code, district, zone_nm, stage, stage_no FROM redev_zone WHERE src = 'gg'")
    hits = [(r, M.match(r, zones), M.stage_of(r.get("현 사업추진단계"))) for r in rows]
    taken = Counter(z["code"] for _, z, _ in hits if z)
    up = [(z["code"], st) for r, z, st in hits if z and st and taken[z["code"]] == 1 and (z["stage_no"] or 0) != 8 and st[1] > (z["stage_no"] or 0)]
    if up:
        db.query("UPDATE redev_zone z SET stage = x.s, stage_no = x.n FROM (VALUES "
                 + ", ".join(f"({lit(c)}, {lit(st[0])}, {st[1]})" for c, st in up) + ") AS x (c, s, n) WHERE z.code = x.c;")
    print(f"  국토부 정비사업 자료: 경기 {len(rows)}구역 중 우리 구역과 연결 {sum(1 for _, z, _ in hits if z)}, 단계 올림 {len(up)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--link-only", action="store_true")
    ap.add_argument("--gg-file", help="경기데이터드림 '일반 정비 사업 추진 현황' CSV(손으로, 선택)")
    ap.add_argument("--molit", action="store_true", help="경기 단계를 국토부 전국 정비사업 자료로 갱신")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        db = connect(a.db)
        today = datetime.now(KST).date()
        rc = load_gg(db, a.gg_file, today) if a.gg_file else load_molit(db) if a.molit else 0 if a.link_only else load(db, today)
        if not rc and not a.link_only:
            log_stages(db, today)
        return rc or run_link(db)
    except (DbError, RuntimeError, OSError, ValueError) as e:
        print(f"[redev] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
