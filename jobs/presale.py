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
from collections import Counter

from collector.db import Db, DbError, connect, lit, select
from collector.infra import dist_m
from collector.presale import (AREAS, PLAN_FILE, address_candidates, locate, match_complex, name_overlap, parse_item, parse_plan,
                              total_households)
from collector.datagokr_file import CaptchaRequired, DownloadError, download
from collector.regions import REGIONS
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
            f"{lit(p['notice_date'])}, {lit(p['house_type'])}, {lit(p['imprmn'])}, {lit(today)})" for p in rows.values()]
    stmts = ["BEGIN;"]
    for i in range(0, len(vals), 500):     # 공고부터 저장 (좌표는 아래에서 나눠 채운다)
        stmts.append("INSERT INTO presale (house_no, name, address, area, households, move_in_ym, notice_date, house_type, imprmn, updated) VALUES "
                     + ", ".join(vals[i:i + 500]) + " ON CONFLICT (house_no) DO UPDATE SET name = EXCLUDED.name, households = EXCLUDED.households, "
                     "move_in_ym = EXCLUDED.move_in_ym, imprmn = EXCLUDED.imprmn, updated = EXCLUDED.updated, "
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
    return link_totals(db) or react(db) or load_plan(db, None)


def load_plan(db: Db, path: str | None) -> int:
    """한국부동산원 입주 예정 물량 파일 → ipju_plan (전부 바꿔 넣는다). 생활권은 이름이 맞는 청약홈 공고(🔧 4글자+, 입주월 ±12개월,
    같은 시군구)의 것, 없으면 같은 법정동 단지들의 다수 생활권."""
    try:
        name, data = (os.path.basename(path), open(path, "rb").read()) if path else download(PLAN_FILE)
    except (CaptchaRequired, DownloadError) as e:
        print(f"  입주 예정 물량 파일 실패: {e}", file=sys.stderr)
        return 2
    rows = parse_plan(data.decode("utf-8-sig", "replace"))
    idx: dict = {}
    for c in select(db, "SELECT region_code, umd_name, lifezone_id FROM complexes WHERE umd_name IS NOT NULL AND lifezone_id IS NOT NULL"):
        sd = REGIONS.get(c["region_code"], " ").split()[0]
        idx.setdefault((sd, c["umd_name"]), Counter())[(c["region_code"], c["lifezone_id"])] += 1
    ps = select(db, "SELECT name, move_in_ym, region_code, lifezone_id FROM presale WHERE lifezone_id IS NOT NULL")
    ym = lambda x: int(x[:4]) * 12 + int(x[4:6])
    by = Counter()
    for r in rows:
        rc, z = locate(r["address"], idx, REGIONS)
        best = max((p for p in ps if (rc is None or p["region_code"] == rc) and abs(ym(p["move_in_ym"]) - ym(r["move_in_ym"])) <= 12),
                   key=lambda p: name_overlap(p["name"], r["name"]), default=None)
        if best and name_overlap(best["name"], r["name"]) >= 4:
            r.update(region_code=best["region_code"], lifezone_id=best["lifezone_id"], locate_by="presale")
        else:
            r.update(region_code=rc, lifezone_id=z, locate_by="dong" if rc else None)
        by[r["locate_by"]] += 1
    today = time.strftime("%Y-%m-%d")
    vals = [f"({lit(r['name'])}, {lit(r['address'])}, {lit(r['area'])}, {lit(r['kind'])}, {r['households']}, {lit(r['move_in_ym'])}, "
            f"{lit(r['region_code'])}, {lit(r['lifezone_id'])}, {lit(r['locate_by'])}, {lit(name)}, {lit(today)})" for r in rows]
    db.query("BEGIN;\nDELETE FROM ipju_plan;\n" + "".join(
        "INSERT INTO ipju_plan (name, address, area, kind, households, move_in_ym, region_code, lifezone_id, locate_by, file_name, loaded) VALUES "
        + ", ".join(vals[i:i + 500]) + ";\n" for i in range(0, len(vals), 500)) + "COMMIT;")
    span = (min(r["move_in_ym"] for r in rows), max(r["move_in_ym"] for r in rows)) if rows else None
    print(f"  입주 예정 물량({name}): 수도권 {len(rows)}개 단지 {sum(r['households'] for r in rows):,}세대, {span}, 위치 {dict(by)}")
    return 0


def react(db: Db) -> int:
    """과거 큰 입주 때 같은 생활권 전세 반응 (sql/f1_react.sql) → presale_react, lifezone.f1_react_*."""
    from datetime import date
    from pathlib import Path
    sql = (Path(__file__).resolve().parent.parent / "sql" / "f1_react.sql").read_text(encoding="utf-8")
    db.query(sql.replace("{TODAY}", lit(date.today())))
    r = select(db, "SELECT count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY rel) AS m FROM presale_react")[0]
    z = select(db, "SELECT count(*) AS n FROM lifezone WHERE f1_react_n IS NOT NULL")[0]["n"]
    print(f"  과거 입주 반응: 사건 {r['n']}건(rel 중앙값 {r['m'] and round(float(r['m']), 2)}%p), 생활권 {z}곳")
    return 0


def link_totals(db: Db) -> int:
    """입주한 공고는 K-apt 세대수로, 입주 전 정비사업 공고는 입주한 정비사업들의 비율로 총 세대를 채운다 (collector/presale.py)."""
    rows = select(db, "SELECT house_no, name, households, move_in_ym, lat, lng, coalesce(imprmn, false) AS imprmn FROM presale")
    cands = [dict(c, lat=float(c["lat"]), lng=float(c["lng"])) for c in select(db, """SELECT c.apt_seq, c.apt_name AS name, c.lat, c.lng,
        c.build_year, k.households FROM complexes c JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
        WHERE c.lat IS NOT NULL AND c.build_year >= 2019 AND k.households > 0""")]
    cur = time.strftime("%Y%m")
    matched, seqs = {}, {}
    for r in rows:
        r["households"] = int(r["households"])
        if r["move_in_ym"] <= cur and r["lat"] is not None:
            c = match_complex(dict(r, lat=float(r["lat"]), lng=float(r["lng"])), cands, dist_m)
            if c:
                matched[r["house_no"]], seqs[r["house_no"]] = (int(c["households"]), c["apt_seq"]), c["apt_seq"]
    ratio, tot = total_households(rows, matched)
    vals = [f"({lit(h)}, {t}, {lit(b)}, {lit(seqs.get(h))})" for h, (t, b) in tot.items()]
    stmts = ["BEGIN;"] + [f"UPDATE presale AS p SET total_hh = v.t, total_basis = v.b, kapt_apt_seq = v.s FROM (VALUES {', '.join(vals[i:i + 1000])}) "
                          "AS v(h, t, b, s) WHERE p.house_no = v.h;" for i in range(0, len(vals), 1000)] + ["COMMIT;"]
    db.query("\n".join(stmts))
    imp = sum(1 for r in rows if r["imprmn"])
    print(f"  총 세대: K-apt 연결 {len(matched)}건(입주한 공고 {sum(1 for r in rows if r['move_in_ym'] <= cur)}건 중), "
          f"정비사업 {imp}건, 비율 {ratio and round(ratio, 2)}, 중복 {sum(1 for t, b in tot.values() if b == '중복')}건")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--geo-limit", type=int, default=1500, help="이번에 좌표를 찾을 공고 수 (SGIS 약 1초/건)")
    ap.add_argument("--link-only", action="store_true", help="API 없이 총 세대 보정 + 과거 입주 반응 + 입주 예정 물량 (DB 만 필요)")
    ap.add_argument("--plan-file", help="입주 예정 물량 파일을 미리 받아 둔 경로 (없으면 공공데이터포털에서 받음)")
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db = connect(a.db)
        rc = (link_totals(db) or react(db) or load_plan(db, a.plan_file)) if a.link_only else run(db, a.geo_limit)
    except (DbError, OSError, KeyError) as e:
        print(f"[presale] 실패: {type(e).__name__} {e}", file=sys.stderr)
        rc = 1
    print(f"[presale] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
