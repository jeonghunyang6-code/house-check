"""H5 서울 정비사업 단계 (collector/redev.py → redev_zone·complex_redev, 0055). SEOUL_API_KEY 가 필요해 Actions(redev.yml)에서 돈다.

    python -m jobs.redev            # 받아서 덮어쓰고 단지 연결
    python -m jobs.redev --link-only   # DB 의 redev_zone 으로 단지 연결만 (클라우드 세션용)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.redev import FIELDS, link, zone_row
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
    db.query(f"BEGIN;\nDELETE FROM redev_zone;\nINSERT INTO redev_zone ({', '.join(COLS)}, fetched_at) VALUES {vals};\nCOMMIT;")
    st = Counter(z["stage"] for z in zones)
    print(f"  서울 정비사업 {len(zones)}개 구역, 단계 {dict(st.most_common())}, 지번 못 읽음 {sum(z['umd_name'] is None for z in zones)}")
    return 0


def run_link(db: Db) -> int:
    zones = select(db, "SELECT code, region_code, zone_nm, biz_type, umd_name, bun FROM redev_zone")
    cx = select(db, "SELECT apt_seq, apt_name, region_code, umd_name, jibun FROM complexes WHERE region_code LIKE '11%'")
    pairs = link(zones, cx)
    stmts = ["BEGIN;", "DELETE FROM complex_redev;"]
    if pairs:
        stmts.append("INSERT INTO complex_redev (apt_seq, code, how) VALUES " + ", ".join(f"({lit(a)}, {lit(c)}, {lit(h)})" for a, c, h in pairs)
                     + " ON CONFLICT DO NOTHING;")
    db.query("\n".join([*stmts, "COMMIT;"]))
    n_reb = sum(1 for z in zones if z["biz_type"] in ("공동주택재건축", "아파트지구재건축"))
    print(f"  재건축 구역 {n_reb}곳 중 {len({c for _, c, _ in pairs})}곳이 단지 {len({a for a, _, _ in pairs})}곳과 연결 "
          f"({dict(Counter(h for _, _, h in pairs))})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--link-only", action="store_true")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        db = connect(a.db)
        rc = 0 if a.link_only else load(db, datetime.now(KST).date())
        return rc or run_link(db)
    except (DbError, RuntimeError, OSError) as e:
        print(f"[redev] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
