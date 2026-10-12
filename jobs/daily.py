"""일일 실거래 스냅샷: 매매·전월세 (docs/ARCHITECTURE.md 4.1).

매일 06:00 KST 에 수도권 시군구 × [당월, 전월] 을 받아 deals·rents / *_events / snapshot_runs 에 반영한다.

    python -m jobs.daily                       # 수도권 전체, 매매+전월세, 당월·전월, DB 경로는 HC_DB_BACKEND (기본 api)
    python -m jobs.daily --regions seoul --kinds trade --db psql
    python -m jobs.daily --regions seoul --months 202001-202508 --bootstrap --skip-done   # 과거 이력 (이어받기)

한 칸이 실패해도 나머지는 계속하고, 실패가 있으면 종료 코드 1 로 끝난다(Actions 에서 빨갛게 보이도록).
호출 한도 초과(QuotaExceeded)면 즉시 멈추고 종료 코드 2. --skip-done 으로 다음 날 이어서 받는다.
비밀 값은 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import DbError, connect
from collector.pg_store import KINDS, apply_snapshot_pg, complexes_sql, done_cells, should_bootstrap
from collector.regions import REGIONS, select_regions
from collector.sources.molit import ApiError, QuotaExceeded, fetch_rents, fetch_trades

FETCH = {"trade": fetch_trades, "rent": fetch_rents}
LABEL = {"trade": "매매", "rent": "전월세"}

KST = ZoneInfo("Asia/Seoul")


def default_months(today: date) -> list[str]:
    prev = date(today.year - (today.month == 1), 12 if today.month == 1 else today.month - 1, 1)
    return [today.strftime("%Y%m"), prev.strftime("%Y%m")]


def parse_months(spec: str) -> list[str]:
    """'202609' | '202608,202609' | '202001-202512'"""
    out: list[str] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            y, m = int(a[:4]), int(a[4:])
            while (y, m) <= (int(b[:4]), int(b[4:])):
                out.append(f"{y}{m:02d}")
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        else:
            out.append(part)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", default="sudogwon", help="sudogwon | seoul | gyeonggi | incheon | 5자리 코드 쉼표 목록")
    ap.add_argument("--months", help="기본: KST 기준 당월·전월")
    ap.add_argument("--kinds", default="trade,rent", help="trade,rent 중 쉼표 목록")
    ap.add_argument("--skip-done", action="store_true", help="snapshot_runs 에 이미 있는 칸은 건너뛴다 (과거 이력 이어받기)")
    ap.add_argument("--db", choices=["api", "psql"], help="기본: HC_DB_BACKEND 또는 api")
    ap.add_argument("--bootstrap", action="store_true", help="first_seen_date 를 NULL 로 (과거 이력 적재용)")
    ap.add_argument("--dry-run", action="store_true", help="API 만 받고 DB 에 쓰지 않는다")
    ap.add_argument("--today", help="테스트용 기준일 YYYY-MM-DD")
    a = ap.parse_args(argv)

    today = date.fromisoformat(a.today) if a.today else datetime.now(KST).date()
    months = parse_months(a.months) if a.months else default_months(today)
    regions = select_regions(a.regions)
    kinds = [KINDS[k.strip()] for k in a.kinds.split(",")]
    db = None if a.dry_run else connect(a.db)
    print(f"[daily] today={today} kinds={[k.name for k in kinds]} regions={len(regions)} "
          f"months={months[0]}..{months[-1]}({len(months)}) dry_run={a.dry_run} skip_done={a.skip_done}")

    failures = skipped = 0
    totals = {"rows": 0, "registered": 0, "cancelled": 0, "disappeared": 0}
    t0 = time.monotonic()
    for kind in kinds:
        done = done_cells(db, kind, regions, months) if (db is not None and a.skip_done) else set()
        for code in regions:
            for ym in months:
                if (code, ym) in done:
                    skipped += 1
                    continue
                tag = f"  {LABEL[kind.name]} {code} {REGIONS[code]} {ym}:"
                try:
                    rows = FETCH[kind.name](code, ym)
                    totals["rows"] += len(rows)
                    if db is None:
                        print(f"{tag} {len(rows)}건 (dry-run)")
                        continue
                    boot = a.bootstrap or should_bootstrap(db, code, ym, today, kind)
                    ev = apply_snapshot_pg(db, code, ym, rows, today, boot, kind)
                    if kind.name == "trade" and rows:
                        db.query(complexes_sql(rows, today))  # 단지 속성 (K-apt 연결용)
                    c = {k: sum(e.event == k for e in ev) for k in ("registered", "cancelled", "disappeared")}
                    for k, v in c.items():
                        totals[k] += v
                    print(f"{tag} {len(rows)}건 신규{c['registered']} 해제{c['cancelled']} "
                          f"사라짐{c['disappeared']}{' [bootstrap]' if boot else ''}")
                except QuotaExceeded as e:
                    print(f"{tag} 호출 한도 초과로 중단: {e}", file=sys.stderr)
                    print(f"[daily] stopped in {time.monotonic() - t0:.0f}s totals={totals} failures={failures}")
                    return 2
                except (ApiError, DbError) as e:
                    failures += 1
                    print(f"{tag} 실패 {e}", file=sys.stderr)
    print(f"[daily] done in {time.monotonic() - t0:.0f}s totals={totals} skipped={skipped} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
