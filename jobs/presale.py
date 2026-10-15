"""청약홈 분양정보 → presale (0034). 입주 물량 F1 은 sql/metrics.sql 8 에서 단지에 붙인다.

    python -m jobs.presale

api.odcloud.kr·SGIS 는 이 클라우드 세션에서 막혀 있어 Actions(presale.yml)에서 돈다. 좌표는 새 공고만 SGIS 로 찾고(지번 → 동),
시군구·생활권은 가장 가까운 단지(🔧 3km 안)에서 가져온다. 공고를 먼저 저장하고 좌표는 100건씩 저장해, 중간에 끊기면 다음 실행이 잇는다.
주소가 바뀐 공고만 좌표를 다시 찾는다. 단지 생활권이 다시 만들어지면(lifezone) 생활권 연결은 다음 좌표 찾기 때까지 옛 값이다.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request

from collector.db import Db, DbError, connect, lit, select
from collector.infra import dist_m
from collector.presale import AREAS, address_candidates, parse_item
from collector.sgis import Sgis, SgisError

URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
NEAR_M = 3000   # 🔧


def fetch(area: str, key: str) -> list[dict]:
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({"page": page, "perPage": 500, "serviceKey": key, "cond[SUBSCRPT_AREA_CODE_NM::EQ]": area})
        for i in range(4):
            try:
                with urllib.request.urlopen(URL + "?" + q, timeout=60) as r:
                    d = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 429):
                    raise
                time.sleep(2 ** i)
            except OSError:
                time.sleep(2 ** i)
        else:
            raise OSError(f"{area} page {page} 실패")
        out += d.get("data", [])
        if page * 500 >= int(d.get("matchCount") or 0):
            return out
        page += 1


def run(db: Db, geo_limit: int) -> int:
    key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    rows = {}
    for area in AREAS:
        got = [p for p in (parse_item(it) for it in fetch(area, key)) if p]
        rows.update({p["house_no"]: p for p in got})
        print(f"  {area}: 공고 {len(got)}건", flush=True)
    today = time.strftime("%Y-%m-%d")
    vals = [f"({lit(p['house_no'])}, {lit(p['name'])}, {lit(p['address'])}, {lit(p['area'])}, {p['households']}, {lit(p['move_in_ym'])}, "
            f"{lit(p['notice_date'])}, {lit(p['house_type'])}, {lit(today)})" for p in rows.values()]
    stmts = ["BEGIN;"]
    for i in range(0, len(vals), 500):     # 공고부터 저장 (좌표는 아래에서 나눠 채운다)
        stmts.append("INSERT INTO presale (house_no, name, address, area, households, move_in_ym, notice_date, house_type, updated) VALUES "
                     + ", ".join(vals[i:i + 500]) + " ON CONFLICT (house_no) DO UPDATE SET name = EXCLUDED.name, households = EXCLUDED.households, "
                     "move_in_ym = EXCLUDED.move_in_ym, updated = EXCLUDED.updated, "
                     "geo_method = CASE WHEN presale.address = EXCLUDED.address THEN presale.geo_method END, address = EXCLUDED.address;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    todo = select(db, f"SELECT house_no, address FROM presale WHERE geo_method IS NULL ORDER BY move_in_ym DESC LIMIT {int(geo_limit)}")
    sg = Sgis()
    cx = [(float(c["lat"]), float(c["lng"]), c["region_code"], c["lifezone_id"])
          for c in select(db, "SELECT lat, lng, region_code, lifezone_id FROM complexes WHERE lat IS NOT NULL")]
    geo_n = {"jibun": 0, "dong": 0, "none": 0}
    batch = []
    for i, p in enumerate(todo, 1):
        lat = lng = rc = z = None
        method = "none"
        for m, addr in address_candidates(p["address"]):
            try:
                hit = sg.geocode(addr)
            except SgisError:
                hit = None
            if hit and hit.get("x") and hit.get("y"):
                lat, lng, method = float(hit["y"]), float(hit["x"]), m
                break
        if lat is not None:
            near = [c for c in cx if abs(c[0] - lat) < 0.03 and abs(c[1] - lng) < 0.04]
            if near:
                d, c = min((dist_m(lat, lng, c[0], c[1]), c) for c in near)
                if d <= NEAR_M:
                    rc, z = c[2], c[3]
        geo_n[method] += 1
        batch.append(f"UPDATE presale SET lat = {lit(lat)}, lng = {lit(lng)}, geo_method = {lit(method)}, region_code = {lit(rc)}, "
                     f"lifezone_id = {lit(z)} WHERE house_no = {lit(p['house_no'])};")
        if len(batch) >= 100 or i == len(todo):
            db.query("BEGIN;\n" + "\n".join(batch) + "\nCOMMIT;")
            batch.clear()
            print(f"  좌표 {i}/{len(todo)} {geo_n}", flush=True)
    left = select(db, "SELECT count(*) AS n FROM presale WHERE geo_method IS NULL")[0]["n"]
    print(f"  공고 {len(rows)}건 저장, 이번에 좌표 {geo_n}, 남은 {left}건")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--geo-limit", type=int, default=1500, help="이번에 좌표를 찾을 공고 수 (SGIS 약 1초/건)")
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run(connect(a.db), a.geo_limit)
    except (DbError, OSError, KeyError) as e:
        print(f"[presale] 실패: {type(e).__name__} {e}", file=sys.stderr)
        rc = 1
    print(f"[presale] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
