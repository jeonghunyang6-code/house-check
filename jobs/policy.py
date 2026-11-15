"""규제 이력·호재 단계 적재 (collector/policy.py → policy_zone·policy_events 0043, collector/projects.py → transit_projects 0046).
원본이 코드라 바꿀 때마다 한 번 돌린다.

    python -m jobs.policy
"""

from __future__ import annotations

import argparse
import json
import sys

from collector.db import DbError, connect, lit, select
from collector.policy import EVENTS, ZONES
from collector.projects import PROJECTS


def statements(geo: dict | None = None) -> str:
    """geo: station_geo 주소 → (위도, 경도). geo_stations 중 좌표를 찾은 것만 new_stations 에 붙인다."""
    geo = geo or {}
    news = lambda p: list(p.new_stations) + [(n, *geo[a]) for n, a in p.geo_stations if a in geo]
    zv = [f"({lit(z.kind)}, {lit(c)}, {lit(u)}, {lit(z.start)}, {lit(z.end)}, {lit(z.scope)}, {lit(z.note)}, {lit(z.source)})"
          for z in ZONES for c in z.region_codes for u in (z.umd_names or (None,))]
    ev = [f"({lit(d)}, {lit(k)}, {lit(t)}, {lit(s)})" for d, k, t, s in EVENTS]
    pv = [f"({lit(p.name)}, {lit(p.status)}, {lit(p.status_date)}, {lit(p.outlook)}, {lit(','.join(p.cbd) or None)}, "
          f"{lit(','.join(p.region_codes))}, {lit(p.source)}, {lit(','.join(p.stations) or None)}, "
          f"{lit(json.dumps([list(x) for x in news(p)], ensure_ascii=False) if news(p) else None)}::jsonb)" for p in PROJECTS]
    return "\n".join([
        "BEGIN;", "DELETE FROM policy_zone;", "DELETE FROM policy_events;", "DELETE FROM transit_projects;",
        "INSERT INTO policy_zone (kind, region_code, umd_name, start_date, end_date, scope, note, source) VALUES " + ", ".join(zv) + ";",
        "INSERT INTO policy_events (event_date, kind, title, source) VALUES " + ", ".join(ev) + ";",
        "INSERT INTO transit_projects (name, status, status_date, outlook, cbd, region_codes, source, stations, new_stations) VALUES " + ", ".join(pv) + ";",
        "COMMIT;"])


def load(db) -> int:
    geo = {r["addr"]: (float(r["lat"]), float(r["lng"])) for r in select(db, "SELECT addr, lat, lng FROM station_geo WHERE lat IS NOT NULL")}
    db.query(statements(geo))
    n = sum(1 for p in PROJECTS for _, a in p.geo_stations if a in geo)
    print(f"  규제 이력: 구역 {sum(len(z.region_codes) * len(z.umd_names or (None,)) for z in ZONES)}행, 사건 {len(EVENTS)}건, 철도 사업 {len(PROJECTS)}건"
          f" (새 역 주소 좌표 {n}/{sum(len(p.geo_stations) for p in PROJECTS)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return load(connect(a.db))
    except DbError as e:
        print(f"[policy] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
