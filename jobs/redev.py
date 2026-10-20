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


def load(db: Db, today) -> int:
    from collector.redev import fetch_all
    zones = [zone_row(r, REGIONS) for r in fetch_all()]
    if not zones:
        print("  서울 정비사업: 0건", file=sys.stderr)
        return 1
    vals = ", ".join("(" + ", ".join([*(lit(z[c]) for c in COLS), lit(today)]) + ")" for z in zones)
    db.query(f"BEGIN;\nDELETE FROM redev_zone WHERE src = 'seoul';\nINSERT INTO redev_zone ({', '.join(COLS)}, fetched_at) VALUES {vals};\nCOMMIT;")
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
    db.query(f"BEGIN;\nDELETE FROM redev_zone WHERE src = 'gg';\nINSERT INTO redev_zone ({', '.join(GG_COLS)}, fetched_at) VALUES {vals};\nCOMMIT;")
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--link-only", action="store_true")
    ap.add_argument("--gg-file", help="경기데이터드림 '일반 정비 사업 추진 현황' CSV")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        db = connect(a.db)
        today = datetime.now(KST).date()
        rc = load_gg(db, a.gg_file, today) if a.gg_file else 0 if a.link_only else load(db, today)
        return rc or run_link(db)
    except (DbError, RuntimeError, OSError, ValueError) as e:
        print(f"[redev] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
