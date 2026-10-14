"""단지 좌표 (collector/sgis.py, 0022). SGIS 는 이 클라우드 세션에서 막혀 있어 Actions(geo.yml)에서 돈다.

    python -m jobs.geo geocode --limit 5000   # 좌표 없는 단지 (최근 거래가 있는 단지 먼저)

주소 후보(지번 → 도로명 → K-apt 도로명)를 차례로 넣고, 돌아온 법정동이 우리 단지의 법정동과 맞을 때만 쓴다.
다 실패하면 geo_method = 'none' 으로 표시하고 다시 부르지 않는다(--retry-none 으로 다시).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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

    for c in todo:
        hit, method = None, "none"
        try:
            rn = REGIONS.get(c["region_code"], "")
            for m, addr in address_candidates(rn, c["umd_name"], c["jibun"], c["road_addr"], c["kapt_road"]):
                h = sg.geocode(addr)
                if accept(h, c["bjd_code"], c["umd_name"], rn):
                    hit, method = h, m
                    break
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["geocode"])
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--retry-none", action="store_true")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run_geocode(connect(a.db), Sgis(), a.limit, a.retry_none, datetime.now(KST).date())
    except (DbError, SgisError) as e:
        print(f"[geo] 실패: {e}", file=sys.stderr)
        rc = 1
    print(f"[geo] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
