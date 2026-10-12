"""R-ONE 주간 지수 적재 (collector/sources/rone.py, 0009).

    python -m jobs.rone weekly     # 마지막으로 받은 주 다음부터 이번 주까지 (매주 목요일 발표 뒤)
    python -m jobs.rone backfill   # 지역마다 전체 시계열 (2012년~). 이미 있는 행은 덮어쓴다

같은 (stat, cls_id, week_id)는 덮어쓰므로 몇 번을 다시 돌려도 된다(발표 후 수정치 반영).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sources.molit import ApiError, QuotaExceeded
from collector.sources.rone import TABLES, Point, fetch_series, fetch_week, keep, map_regions, weeks_between

KST = ZoneInfo("Asia/Seoul")
CHUNK = 1000


def upsert(db: Db, stat: str, pts: list[Point]) -> int:
    pts = [p for p in pts if keep(stat, p)]
    if not pts:
        return 0
    regions = {p.cls_id: p for p in pts}
    rmap = map_regions([p.full_name for p in regions.values()], REGIONS)
    stmts = ["BEGIN;"]
    rv = ", ".join(f"({p.cls_id}, {lit(p.full_name)}, {lit(p.name)}, {lit(rmap.get(p.full_name))})" for p in regions.values())
    stmts.append("INSERT INTO rone_regions (cls_id, full_name, name, region_code) VALUES " + rv +
                 " ON CONFLICT (cls_id) DO UPDATE SET full_name = EXCLUDED.full_name, name = EXCLUDED.name, "
                 "region_code = COALESCE(EXCLUDED.region_code, rone_regions.region_code);")
    for i in range(0, len(pts), CHUNK):
        vals = ", ".join(f"({lit(stat)}, {p.cls_id}, {lit(p.week_id)}, {lit(p.week_date)}, {lit(p.value)})" for p in pts[i:i + CHUNK])
        stmts.append("INSERT INTO rone_weekly (stat, cls_id, week_id, week_date, value) VALUES " + vals +
                     " ON CONFLICT (stat, cls_id, week_id) DO UPDATE SET value = EXCLUDED.value, week_date = EXCLUDED.week_date;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    return len(pts)


def run_weekly(db: Db, today: date) -> int:
    rc = 0
    for stat in TABLES:
        last = select(db, f"SELECT max(week_date)::text AS d FROM rone_weekly WHERE stat = {lit(stat)}")[0]["d"]
        start = date.fromisoformat(last) + timedelta(days=7) if last else today - timedelta(days=21)
        for wk in weeks_between(start, today):
            try:
                n = upsert(db, stat, fetch_week(stat, wk))
            except QuotaExceeded as e:
                print(f"  {stat} {wk}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
                return 2
            except (ApiError, DbError) as e:
                print(f"  {stat} {wk}: 실패 {e}", file=sys.stderr)
                rc = 1
                continue
            print(f"  {stat} {wk}: {n}행" if n else f"  {stat} {wk}: 아직 발표 없음")
    return rc


def run_backfill(db: Db) -> int:
    rc = 0
    for stat in TABLES:
        try:
            latest = _latest_points(stat)
        except (ApiError, QuotaExceeded) as e:
            print(f"  {stat}: 최신 주 조회 실패 {e}", file=sys.stderr)
            rc = 1
            continue
        cls_ids = sorted({p.cls_id for p in latest if keep(stat, p)})
        total = 0
        for cid in cls_ids:
            try:
                total += upsert(db, stat, fetch_series(stat, cid))
            except QuotaExceeded as e:
                print(f"  {stat} {cid}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
                return 2
            except (ApiError, DbError) as e:
                print(f"  {stat} {cid}: 실패 {e}", file=sys.stderr)
                rc = 1
        print(f"  {stat}: 지역 {len(cls_ids)}개, {total}행")
    return rc


def _latest_points(stat: str) -> list[Point]:
    """최근 4주 중 발표가 있는 가장 최근 주의 전체 지역 (backfill 할 지역 목록을 정하는 데 쓴다)."""
    today = datetime.now(KST).date()
    for wk in reversed(weeks_between(today - timedelta(days=28), today)):
        pts = fetch_week(stat, wk)
        if pts:
            return pts
    raise ApiError("최근 4주 발표 없음")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["weekly", "backfill"])
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    db = connect(a.db)
    t0 = time.monotonic()
    rc = run_weekly(db, datetime.now(KST).date()) if a.mode == "weekly" else run_backfill(db)
    print(f"[rone] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
