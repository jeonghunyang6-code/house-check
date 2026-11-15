"""새로 생기는 역(가칭) 좌표 (station_geo, 0084) → 철도 사업 다시 적재(jobs/policy.py).

collector/projects.py 의 geo_stations((역 이름, 주소))에서 아직 좌표가 없는 주소만 네이버 클라우드 Geocoding 으로 찾는다.
키는 길찾기·정비구역과 같은 NCP_MAPS_KEY_ID·NCP_MAPS_KEY(이 클라우드 세션에는 없어 GitHub 자동 작업 station_geo.yml 에서 돈다).
401·403·429 면 멈춘다. 역 위치가 공개되지 않아 기사에 나온 지점 근처 주소로 잡는 근사 좌표다(사실표·지도에 '가칭').

    python -m jobs.station_geo            # 없는 주소만
    python -m jobs.station_geo --redo     # 전부 다시
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from collector.db import Db, DbError, connect, lit, select
from collector.projects import PROJECTS
from jobs import policy
from jobs.redev_geo import URL, Stop


def addrs() -> list[str]:
    return sorted({a for p in PROJECTS for _, a in p.geo_stations})


def geocode(q: str, kid: str, key: str, opener=urllib.request.urlopen) -> tuple[float, float, str] | None:
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode({'query': q})}", headers={"x-ncp-apigw-api-key-id": kid, "x-ncp-apigw-api-key": key})
    try:
        with opener(req, timeout=20) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Stop(f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}") from None
        return None
    a = (d.get("addresses") or [None])[0]
    return (round(float(a["y"]), 5), round(float(a["x"]), 5), a.get("roadAddress") or a.get("jibunAddress") or "") if a else None


def run(db: Db, redo: bool) -> int:
    want = addrs()
    have = set() if redo else {r["addr"] for r in select(db, "SELECT addr FROM station_geo WHERE lat IS NOT NULL")}
    todo = [a for a in want if a not in have]
    kid, key = os.environ.get("NCP_MAPS_KEY_ID", ""), os.environ.get("NCP_MAPS_KEY", "")
    print(f"  새 역 주소 {len(want)}곳 중 찾을 것 {len(todo)}곳")
    if todo and not (kid and key):
        print("  NCP_MAPS_KEY_ID·NCP_MAPS_KEY 없음 → Geocoding 건너뜀")
    elif todo:
        rows = []
        try:
            for a in todo:
                g = geocode(a, kid, key)
                rows.append(f"({lit(a)}, {g[0] if g else 'NULL'}, {g[1] if g else 'NULL'}, {lit(g[2] if g else None)}, now())")
                print(f"  {a} → {f'{g[0]}, {g[1]} ({g[2]})' if g else '못 찾음'}")
        except Stop as e:
            print(f"  멈춤: {e}", file=sys.stderr)
        if rows:
            db.query("INSERT INTO station_geo (addr, lat, lng, road, geocoded_at) VALUES " + ", ".join(rows)
                     + " ON CONFLICT (addr) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, road = EXCLUDED.road, geocoded_at = EXCLUDED.geocoded_at;")
    return policy.load(db)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.redo)
    except DbError as e:
        print(f"[station_geo] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
