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
from collector.presale import (AREAS, PLAN_FILE, address_candidates, locate, match_complex, name_overlap, parse_item, parse_models,
                              parse_plan, total_households)
from collector.datagokr_file import CaptchaRequired, DownloadError, download
from collector.regions import REGIONS
from collector.sgis import Sgis, SgisError

URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
URL_MDL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl"   # 주택형별 (분양가)
RATIO_MONTHS = 24   # 🔧 분양가 ÷ 주변 시세는 최근 24개월 공고만 (주변 시세가 지금 값이라 오래된 공고는 비교가 안 된다)
# 공공주택은 분양가를 정책으로 정해(시세 연동 아님) 비교에서 뺀다. 신혼희망타운 추가 모집 공고에는 10배 값도 있었다(2026-10-18)
PUBLIC_RE = "신혼희망|공공임대|공공분양|분양전환|행복주택|국민임대|뉴홈|장기전세|공공지원|토지임대부"
NEAR_M = 3000   # 🔧


def fetch(area: str | None, key: str, url: str = URL) -> list[dict]:
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({"page": page, "perPage": 500, "serviceKey": key,
                                    **({"cond[SUBSCRPT_AREA_CODE_NM::EQ]": area} if area else {})})
        for i in range(4):
            try:
                with urllib.request.urlopen(url + "?" + q, timeout=60) as r:
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
    return link_totals(db) or react(db) or load_plan(db, None) or prices(db, key) or price_ratio(db)


def prices(db: Db, key: str) -> int:
    """청약홈 주택형별 → presale 분양가 (0042). 전국 전체를 받아 우리 공고만 쓴다(지역 조건이 없는 API)."""
    items = fetch(None, key, URL_MDL)
    if items and not {"HOUSE_MANAGE_NO", "HOUSE_TY", "LTTOT_TOP_AMOUNT"} <= set(items[0]):
        print(f"  주택형별 응답 칸이 예상과 다름: {sorted(items[0])}", file=sys.stderr)
        return 2
    got = parse_models(items)
    ours = {r["house_no"] for r in select(db, "SELECT house_no FROM presale")}
    vals = [f"({lit(h)}, {lit(v['price_ppm_10k'])}, {lit(v['price84_10k'])}, {v['price_types']})" for h, v in got.items() if h in ours]
    stmts = ["BEGIN;"] + [f"UPDATE presale AS p SET price_ppm_10k = v.a::numeric, price84_10k = v.b::int, price_types = v.n "
                          f"FROM (VALUES {', '.join(vals[i:i + 1000])}) AS v(h, a, b, n) WHERE p.house_no = v.h;"
                          for i in range(0, len(vals), 1000)] + ["COMMIT;"]
    if vals:
        db.query("\n".join(stmts))
    print(f"  분양가: 주택형 {len(items):,}행(전국 공고 {len(got):,}건) → 우리 공고 {len(vals):,}/{len(ours):,}건, "
          f"가격 있음 {sum(1 for h, v in got.items() if h in ours and v['price_ppm_10k']):,}건")
    return 0


def price_ratio(db: Db) -> int:
    """F3 분양가 과다형 구분: 최근 공고의 ㎡당 분양가 ÷ 같은 생활권 단지 ㎡당 기준 시세 중앙값(🔧 3곳 미만이면 반경 1.5km),
    그리고 ÷ 같은 생활권 신축(E7) ㎡당 시세. 그 공고 단지 자신(kapt_apt_seq)은 비교에서 뺀다."""
    db.query(f"""BEGIN;
UPDATE presale SET price_ratio = NULL, price_ratio_new = NULL, price_ref_n = NULL;
WITH m AS (
  SELECT c.apt_seq, c.lifezone_id AS z, c.lat, c.lng, percentile_cont(0.5) WITHIN GROUP (ORDER BY x.ref_10k::numeric / x.area_group) AS ppm
  FROM complex_metrics x JOIN complexes c USING (apt_seq) WHERE x.ref_10k IS NOT NULL AND x.area_group BETWEEN 40 AND 135 GROUP BY 1, 2, 3, 4
), p AS (
  SELECT house_no, lifezone_id AS z, lat, lng, kapt_apt_seq, price_ppm_10k FROM presale
  WHERE price_ppm_10k IS NOT NULL AND notice_date >= current_date - INTERVAL '{RATIO_MONTHS} months'
    AND house_type = 'APT' AND name !~ {lit(PUBLIC_RE)}
), zr AS (
  SELECT p.house_no, percentile_cont(0.5) WITHIN GROUP (ORDER BY m.ppm) AS ref, count(*) AS n
  FROM p JOIN m ON m.z = p.z AND m.apt_seq IS DISTINCT FROM p.kapt_apt_seq GROUP BY 1
), rr AS (
  SELECT p.house_no, percentile_cont(0.5) WITHIN GROUP (ORDER BY m.ppm) AS ref, count(*) AS n
  FROM p JOIN m ON p.lat IS NOT NULL AND m.lat IS NOT NULL AND abs(m.lat - p.lat) < 0.014 AND abs(m.lng - p.lng) < 0.018
    AND 111320 * sqrt(power(m.lat - p.lat, 2) + power((m.lng - p.lng) * 0.7934, 2)) <= 1500 AND m.apt_seq IS DISTINCT FROM p.kapt_apt_seq
  GROUP BY 1
)
UPDATE presale t SET
  price_ratio = round((p.price_ppm_10k / CASE WHEN zr.n >= 3 THEN zr.ref ELSE rr.ref END)::numeric, 2),
  price_ref_n = CASE WHEN zr.n >= 3 THEN zr.n ELSE rr.n END,
  price_ratio_new = round((p.price_ppm_10k / nullif(l.e7_new_ppm, 0))::numeric, 2)
FROM p LEFT JOIN zr USING (house_no) LEFT JOIN rr USING (house_no) LEFT JOIN lifezone l ON l.zone_id = p.z
WHERE t.house_no = p.house_no AND (zr.n >= 3 OR rr.n >= 3 OR l.e7_new_ppm IS NOT NULL);
COMMIT;""")
    r = select(db, f"""SELECT count(*) FILTER (WHERE price_ppm_10k IS NOT NULL AND notice_date >= current_date - INTERVAL '{RATIO_MONTHS} months'
        AND house_type = 'APT' AND name !~ {lit(PUBLIC_RE)}) AS n,
      count(price_ratio) AS nr, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_ratio) AS mr,
      count(price_ratio_new) AS nn, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_ratio_new) AS mn FROM presale""")[0]
    print(f"  분양가 ÷ 주변 시세: 최근 {RATIO_MONTHS}개월 민영 공고 {r['n']}건 중 {r['nr']}건(중앙값 {r['mr'] and round(float(r['mr']), 2)}), "
          f"÷ 신축 {r['nn']}건(중앙값 {r['mn'] and round(float(r['mn']), 2)})")
    return 0


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


def react(db: Db, store=None) -> int:
    """과거 큰 입주 때 같은 생활권 전세 반응 (collector/react.py) → presale_react, lifezone.f1_react_*.
    전세 요약은 DB(rent_monthly, 최근 17개월) + 보관 파일(rentsum_<시군구>, 그 전)."""
    from datetime import date
    from collector.archive import open_store
    from collector.react import MIN_HH, SINCE, add_months, react_rows, zone_summary
    from collector.regions import REGIONS
    from jobs.rent_archive import iter_sums
    store = store or open_store(None)
    last = add_months(f"{date.today():%Y%m}", -7)
    events = [dict(r, sd={"서울": "11", "경기": "41", "인천": "28"}[r["area"]]) for r in select(db, f"""
SELECT house_no, lifezone_id AS z, move_in_ym, coalesce(total_hh, households) AS hh, area FROM presale
WHERE coalesce(total_hh, households) >= {MIN_HH} AND lifezone_id IS NOT NULL AND area IN ('서울', '경기', '인천')
  AND move_in_ym BETWEEN '202101' AND {lit(last)}""")]
    cx = {r["apt_seq"]: (r["z"], int(r["by"]) if r["by"] is not None else None)
          for r in select(db, "SELECT apt_seq, lifezone_id AS z, build_year AS by FROM complexes")}
    seen, rents = set(), []
    for r in select(db, "SELECT apt_seq, area_group, contract_month, jeonse_median_10k, n_jeonse, region_code FROM rent_monthly "
                        f"WHERE jeonse_median_10k > 0 AND n_jeonse > 0 AND contract_month >= {lit(SINCE)}"):
        seen.add((r["apt_seq"], int(r["area_group"]), r["contract_month"]))
        rents.append((r["apt_seq"], int(r["area_group"]), r["contract_month"], float(r["jeonse_median_10k"]), int(r["n_jeonse"]), r["region_code"][:2]))
    n_file = 0
    for r in iter_sums(store, sorted(REGIONS), SINCE):
        k = (r["apt_seq"], int(r["area_group"]), r["contract_month"])
        if k in seen or not r["jeonse_median_10k"] or int(r["n_jeonse"]) <= 0 or int(r["jeonse_median_10k"]) <= 0:
            continue
        rents.append((k[0], k[1], k[2], float(r["jeonse_median_10k"]), int(r["n_jeonse"]), r["region_code"][:2]))
        n_file += 1
    rows = react_rows(events, rents, cx)
    cols = ("house_no", "lifezone_id", "move_in_ym", "total_hh", "zone_chg", "base_chg", "rel", "n")
    stmts = ["BEGIN;", "DELETE FROM presale_react;"]
    if rows:
        stmts.append(f"INSERT INTO presale_react ({', '.join(cols)}) VALUES "
                     + ", ".join("(" + ", ".join(lit(r[c]) for c in cols) + ")" for r in rows) + ";")
    stmts.append("UPDATE lifezone SET f1_react_rel = NULL, f1_react_n = NULL;")
    zs = zone_summary(rows)
    if zs:
        stmts.append("UPDATE lifezone l SET f1_react_rel = v.r, f1_react_n = v.n FROM (VALUES "
                     + ", ".join(f"({lit(z)}, {lit(r)}::numeric, {n})" for z, (r, n) in zs.items()) + ") AS v(z, r, n) WHERE l.zone_id = v.z;")
    db.query("\n".join(stmts + ["COMMIT;"]))
    rel = sorted(r["rel"] for r in rows if r["rel"] is not None)
    print(f"  과거 입주 반응: 큰 입주 {len(events)}건 중 {len(rows)}건(rel 중앙값 {rel[len(rel) // 2] if rel else '-'}%p), "
          f"생활권 {len(zs)}곳 (전세 요약 DB {len(rents) - n_file:,}행 + 보관 파일 {n_file:,}행)")
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
    ap.add_argument("--prices-only", action="store_true", help="분양가(주택형별)만 받고 주변 시세와 비교")
    ap.add_argument("--plan-file", help="입주 예정 물량 파일을 미리 받아 둔 경로 (없으면 공공데이터포털에서 받음)")
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        db = connect(a.db)
        if a.prices_only:
            rc = prices(db, os.environ["DATA_GO_KR_SERVICE_KEY"]) or price_ratio(db)
        elif a.link_only:
            rc = link_totals(db) or react(db) or load_plan(db, a.plan_file) or price_ratio(db)
        else:
            rc = run(db, a.geo_limit)
    except (DbError, OSError, KeyError) as e:
        print(f"[presale] 실패: {type(e).__name__} {e}", file=sys.stderr)
        rc = 1
    print(f"[presale] done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
