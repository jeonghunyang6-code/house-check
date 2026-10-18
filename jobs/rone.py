"""R-ONE 주간 지수 적재 (collector/sources/rone.py, 0009).

    python -m jobs.rone weekly     # 마지막으로 받은 주 다음부터 이번 주까지 (매주 목요일 발표 뒤)
    python -m jobs.rone backfill   # 지역마다 전체 시계열 (2012년~). 이미 있는 행은 덮어쓴다
    python -m jobs.rone breadth --weeks 8   # 최근 N주의 전국·수도권 상승·하락 지역 수 (rone_breadth, 0011)
    python -m jobs.rone buyer      # 매입자 거주지별 아파트 매매 (월간, buyer_residence, 0044)

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
from collector.market import breadth
from collector.sources.rone import (CAPITAL_PREFIXES, TABLES, Point, buyer_codes, fetch_buyer_month, fetch_series, fetch_week, keep, map_regions,
                                    weeks_between)

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


def store_breadth(db: Db, stat: str, cur: list[Point], prev: list[Point]) -> None:
    """한 주 전체 응답(전국 모든 지역)과 직전 발표 주 → 전국·수도권 상승·하락 말단 지역 수."""
    c = {p.full_name: p.value for p in cur}
    pv = {p.full_name: p.value for p in prev}
    w = cur[0]
    vals = []
    for scope, keep_name in (("전국", lambda n: True), ("수도권", lambda n: n.split(">")[0] in CAPITAL_PREFIXES)):
        n, up, down = breadth({k: v for k, v in c.items() if keep_name(k)}, {k: v for k, v in pv.items() if keep_name(k)})
        vals.append(f"({lit(stat)}, {lit(w.week_id)}, {lit(w.week_date)}, {lit(scope)}, {n}, {up}, {down})")
    db.query("INSERT INTO rone_breadth (stat, week_id, week_date, scope, n, n_up, n_down) VALUES " + ", ".join(vals) +
             " ON CONFLICT (stat, week_id, scope) DO UPDATE SET n = EXCLUDED.n, n_up = EXCLUDED.n_up, n_down = EXCLUDED.n_down;")


def prev_published(stat: str, d: date) -> list[Point]:
    """d 주 직전의 발표 주 (추석처럼 건너뛴 주가 있으면 그 앞 주)."""
    for back in (7, 14, 21):
        pts = fetch_week(stat, weeks_between(d - timedelta(days=back), d - timedelta(days=back))[0])
        if pts:
            return pts
    return []


def run_breadth(db: Db, weeks: int, today: date) -> int:
    rc = 0
    for stat in ("sale", "jeonse"):
        for wk in weeks_between(today - timedelta(days=7 * weeks), today):
            try:
                cur = fetch_week(stat, wk)
                if cur:
                    store_breadth(db, stat, cur, prev_published(stat, cur[0].week_date))
                    print(f"  breadth {stat} {wk}: 저장")
            except QuotaExceeded as e:
                print(f"  breadth {stat} {wk}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
                return 2
            except (ApiError, DbError) as e:
                print(f"  breadth {stat} {wk}: 실패 {e}", file=sys.stderr)
                rc = 1
    return rc


def run_weekly(db: Db, today: date) -> int:
    rc = 0
    for stat in TABLES:
        last = select(db, f"SELECT max(week_date)::text AS d FROM rone_weekly WHERE stat = {lit(stat)}")[0]["d"]
        start = date.fromisoformat(last) + timedelta(days=7) if last else today - timedelta(days=21)
        for wk in weeks_between(start, today):
            try:
                pts = fetch_week(stat, wk)
                n = upsert(db, stat, pts)
                if pts and stat in ("sale", "jeonse"):
                    store_breadth(db, stat, pts, prev_published(stat, pts[0].week_date))
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


BUYER_START = "202001"
BUYER_REVISE = 3   # 최근 몇 달은 다시 받는다(늦은 신고로 바뀐다)


def run_buyer(db: Db, today: date) -> int:
    """매입자 거주지별 아파트 매매 (buyer_residence, 0044). 처음엔 2020-01 부터, 이후엔 저장된 마지막 달의 3달 전부터 지난달까지."""
    last = select(db, "SELECT max(period) AS p FROM buyer_residence")[0]["p"]
    ym = BUYER_START if not last else _ym_add(last, -BUYER_REVISE)
    end = _ym_add(today.strftime("%Y%m"), -1)
    rc, n_months = 0, 0
    while ym <= end:
        try:
            rows = fetch_buyer_month(ym)
        except QuotaExceeded as e:
            print(f"  매입자 거주지 {ym}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
            return 2
        except ApiError as e:
            print(f"  매입자 거주지 {ym}: 실패 {e}", file=sys.stderr)
            rc = 1
            ym = _ym_add(ym, 1)
            continue
        if rows:
            vals = ", ".join("(" + ", ".join(lit(x) for x in (r["period"], r["grp_id"], r["name"],
                                                                ",".join(buyer_codes(r["name"], REGIONS)) or None, r["total"],
                                                                r.get("same_sgg"), r.get("same_sido"), r.get("seoul"), r.get("other"))) + ")"
                             for r in rows)
            db.query("INSERT INTO buyer_residence (period, grp_id, name, region_codes, total, same_sgg, same_sido, seoul, other) VALUES "
                     + vals + " ON CONFLICT (period, grp_id) DO UPDATE SET name = EXCLUDED.name, region_codes = EXCLUDED.region_codes, "
                     "total = EXCLUDED.total, same_sgg = EXCLUDED.same_sgg, same_sido = EXCLUDED.same_sido, seoul = EXCLUDED.seoul, other = EXCLUDED.other;")
            n_months += 1
        print(f"  매입자 거주지 {ym}: {len(rows)}개 지역" if rows else f"  매입자 거주지 {ym}: 아직 발표 없음", flush=True)
        ym = _ym_add(ym, 1)
    return rc


def _ym_add(ym: str, k: int) -> str:
    y, m = divmod(int(ym[:4]) * 12 + int(ym[4:]) - 1 + k, 12)
    return f"{y}{m + 1:02d}"


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
    ap.add_argument("mode", choices=["weekly", "backfill", "breadth", "buyer"])
    ap.add_argument("--weeks", type=int, default=8, help="breadth 모드: 최근 몇 주")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    db = connect(a.db)
    t0 = time.monotonic()
    today = datetime.now(KST).date()
    rc = (run_weekly(db, today) if a.mode == "weekly" else run_backfill(db) if a.mode == "backfill"
          else run_buyer(db, today) if a.mode == "buyer" else run_breadth(db, a.weeks, today))
    print(f"[rone] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
