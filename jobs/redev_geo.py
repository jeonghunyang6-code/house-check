"""정비구역 좌표 (redev_zone.lat·lng, 0074). 상세 탭 실제 지도(네이버 지도)에 정비구역을 찍는 데 쓴다.

    python -m jobs.redev_geo            # 좌표 없는 구역만
    python -m jobs.redev_geo --redo     # 전부 다시

① 같은 시군구·동·지번 단지(complexes) 좌표 ② 없으면 네이버 클라우드 Geocoding('시도 시군구 동 번-지') — 키는 길찾기와 같은
NCP_MAPS_KEY_ID·NCP_MAPS_KEY(Maps Application 에 Geocoding 사용 체크 필요). 401·403·429 면 멈춘다. 구역의 대표 지번 한 점이라 넓은 구역은 실제 경계와 다르다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS

URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
SIDO = {"11": "서울특별시", "28": "인천광역시", "41": "경기도"}


class Stop(RuntimeError):
    pass


def query_of(z: dict) -> str:
    sgg = " ".join(REGIONS.get(z["region_code"], "").split()[1:])
    jb = f"{z['bun']}" + (f"-{z['ji']}" if z.get("ji") else "")
    return f"{SIDO.get(z['region_code'][:2], '')} {sgg} {z['umd_name']} {jb}".strip()


def geocode(q: str, kid: str, key: str, opener=urllib.request.urlopen) -> tuple[float, float] | None:
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode({'query': q})}", headers={"x-ncp-apigw-api-key-id": kid, "x-ncp-apigw-api-key": key})
    try:
        with opener(req, timeout=20) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Stop(f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}") from None
        return None
    a = (d.get("addresses") or [None])[0]
    return (float(a["y"]), float(a["x"])) if a else None


def run(db: Db, redo: bool) -> int:
    if redo:
        db.query("UPDATE redev_zone SET lat = NULL, lng = NULL, geo_src = NULL;")
    db.query("""UPDATE redev_zone z SET lat = c.lat, lng = c.lng, geo_src = 'complex' FROM (
  SELECT DISTINCT ON (z2.code) z2.code, c.lat, c.lng FROM redev_zone z2 JOIN complexes c ON c.region_code = z2.region_code AND c.umd_name = z2.umd_name
    AND c.jibun = z2.bun::text || CASE WHEN coalesce(z2.ji, 0) > 0 THEN '-' || z2.ji ELSE '' END AND c.lat IS NOT NULL
  WHERE z2.lat IS NULL ORDER BY z2.code) c WHERE z.code = c.code;""")
    todo = select(db, "SELECT code, region_code, umd_name, bun, ji FROM redev_zone WHERE lat IS NULL AND geo_src IS DISTINCT FROM 'none' AND bun IS NOT NULL AND umd_name IS NOT NULL")
    kid, key = os.environ.get("NCP_MAPS_KEY_ID", ""), os.environ.get("NCP_MAPS_KEY", "")
    print(f"  단지 지번으로 채움 뒤 남은 {len(todo)}곳")
    if todo and not (kid and key):
        print("  NCP_MAPS_KEY_ID·NCP_MAPS_KEY 없음 → Geocoding 건너뜀")
        return 0
    got, miss = [], []
    try:
        for i, z in enumerate(todo):
            p = geocode(query_of(z), kid, key)
            (got if p else miss).append((z["code"], p))
            if i and i % 9 == 0:
                time.sleep(1)
    except Stop as e:
        print(f"  멈춤: {e}", file=sys.stderr)
    if got:
        db.query("UPDATE redev_zone z SET lat = x.la, lng = x.lo, geo_src = 'ncp' FROM (VALUES "
                 + ", ".join(f"({lit(c)}, {p[0]}, {p[1]})" for c, p in got) + ") AS x (c, la, lo) WHERE z.code = x.c;")
    if miss:
        db.query("UPDATE redev_zone SET geo_src = 'none' WHERE code IN (" + ", ".join(lit(c) for c, _ in miss) + ");")
    s = select(db, "SELECT count(*) n, count(lat) geo, count(*) FILTER (WHERE geo_src = 'complex') cx, count(*) FILTER (WHERE geo_src = 'ncp') ncp FROM redev_zone")[0]
    print(f"  정비구역 {s['n']}곳 중 좌표 {s['geo']}(단지 {s['cx']} · Geocoding {s['ncp']}), 이번 Geocoding 성공 {len(got)} · 못 찾음 {len(miss)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.redo)
    except DbError as e:
        print(f"[redev_geo] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
