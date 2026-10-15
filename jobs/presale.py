"""청약홈 분양정보 → presale (0034). 입주 물량 F1 은 sql/metrics.sql 8 에서 단지에 붙인다.

    python -m jobs.presale

api.odcloud.kr·SGIS 는 이 클라우드 세션에서 막혀 있어 Actions(presale.yml)에서 돈다. 좌표는 새 공고만 SGIS 로 찾고(지번 → 동),
시군구·생활권은 가장 가까운 단지(🔧 3km 안)에서 가져온다.
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


def run(db: Db) -> int:
    key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    rows = {}
    for area in AREAS:
        got = [p for p in (parse_item(it) for it in fetch(area, key)) if p]
        rows.update({p["house_no"]: p for p in got})
        print(f"  {area}: 공고 {len(got)}건", flush=True)
    have = {r["house_no"]: r for r in select(db, "SELECT house_no, lat, lng, geo_method FROM presale")}
    sg = Sgis()
    geo_n = {"jibun": 0, "dong": 0, "none": 0}
    for p in rows.values():
        h = have.get(p["house_no"])
        if h and h["geo_method"]:
            p.update(lat=h["lat"], lng=h["lng"], geo_method=h["geo_method"])
            continue
        p.update(lat=None, lng=None, geo_method="none")
        for method, addr in address_candidates(p["address"]):
            try:
                hit = sg.geocode(addr)
            except SgisError:
                hit = None
            if hit and hit.get("x") and hit.get("y"):
                p.update(lat=float(hit["y"]), lng=float(hit["x"]), geo_method=method)
                break
        geo_n[p["geo_method"]] += 1
    cx = [(float(c["lat"]), float(c["lng"]), c["region_code"], c["lifezone_id"])
          for c in select(db, "SELECT lat, lng, region_code, lifezone_id FROM complexes WHERE lat IS NOT NULL")]
    for p in rows.values():
        p["region_code"] = p["lifezone_id"] = None
        if p["lat"] is None:
            continue
        near = [c for c in cx if abs(c[0] - p["lat"]) < 0.03 and abs(c[1] - p["lng"]) < 0.04]
        if near:
            d, c = min((dist_m(p["lat"], p["lng"], c[0], c[1]), c) for c in near)
            if d <= NEAR_M:
                p["region_code"], p["lifezone_id"] = c[2], c[3]
    today = time.strftime("%Y-%m-%d")
    vals = [f"({lit(p['house_no'])}, {lit(p['name'])}, {lit(p['address'])}, {lit(p['area'])}, {p['households']}, {lit(p['move_in_ym'])}, "
            f"{lit(p['notice_date'])}, {lit(p['house_type'])}, {lit(p['lat'])}, {lit(p['lng'])}, {lit(p['geo_method'])}, "
            f"{lit(p['region_code'])}, {lit(p['lifezone_id'])}, {lit(today)})" for p in rows.values()]
    stmts = ["BEGIN;"]
    for i in range(0, len(vals), 500):
        stmts.append("INSERT INTO presale (house_no, name, address, area, households, move_in_ym, notice_date, house_type, lat, lng, geo_method, "
                     "region_code, lifezone_id, updated) VALUES " + ", ".join(vals[i:i + 500]) +
                     " ON CONFLICT (house_no) DO UPDATE SET name = EXCLUDED.name, address = EXCLUDED.address, households = EXCLUDED.households, "
                     "move_in_ym = EXCLUDED.move_in_ym, lat = EXCLUDED.lat, lng = EXCLUDED.lng, geo_method = EXCLUDED.geo_method, "
                     "region_code = EXCLUDED.region_code, lifezone_id = EXCLUDED.lifezone_id, updated = EXCLUDED.updated;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    linked = sum(1 for p in rows.values() if p["region_code"])
    print(f"  공고 {len(rows)}건 저장, 새로 좌표 찾기 {geo_n}, 시군구 연결 {linked}건")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        rc = run(connect(a.db))
    except (DbError, OSError, KeyError) as e:
        print(f"[presale] 실패: {type(e).__name__} {e}", file=sys.stderr)
        rc = 1
    print(f"[presale] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
