"""직장까지 자차 시간 (collector/drive.py → complex_drive, 0066). drive.yml 이 평일 아침에 돈다(이미 받은 단지는 건너뜀).
대상 = 기준 시세가 있는(찾기 탭 후보) 좌표 있는 단지 약 6,700곳 × 목적지 2곳.

    python -m jobs.drive --limit 3000            # 이번에 부를 최대 횟수
    python -m jobs.drive --refresh-days 120      # 이보다 오래된 값은 다시
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from collector import drive as V
from collector.db import Db, DbError, connect, lit, select

KST = ZoneInfo("Asia/Seoul")


def targets(db: Db, refresh_days: int) -> list[dict]:
    return select(db, f"""SELECT c.apt_seq, c.lat, c.lng, d.dest FROM complexes c
CROSS JOIN (VALUES {', '.join(f'({lit(k)})' for k in V.DESTS)}) AS d (dest)
WHERE c.lat IS NOT NULL AND c.apt_seq IN (SELECT apt_seq FROM complex_metrics WHERE ref_10k IS NOT NULL OR a5_est_10k IS NOT NULL)
  AND NOT EXISTS (SELECT 1 FROM complex_drive x WHERE x.apt_seq = c.apt_seq AND x.dest = d.dest AND x.fetched_at > now() - make_interval(days => {int(refresh_days)}))
ORDER BY c.apt_seq, d.dest""")


def save(db: Db, rows: list[tuple]) -> None:
    if rows:
        db.query("INSERT INTO complex_drive (apt_seq, dest, minutes, km, fetched_at) VALUES "
                 + ", ".join(f"({lit(a)}, {lit(d)}, {lit(m)}, {lit(k)}, now())" for a, d, m, k in rows)
                 + " ON CONFLICT (apt_seq, dest) DO UPDATE SET minutes = EXCLUDED.minutes, km = EXCLUDED.km, fetched_at = EXCLUDED.fetched_at;")


def run(db: Db, limit: int, refresh_days: int, opener=None) -> int:
    kid, key = V.keys()
    todo = targets(db, refresh_days)[:limit]
    print(f"  자차 시간: 남은 {len(todo):,}건 (이번 최대 {limit:,})")
    if not todo:
        return 0
    kw = {"opener": opener} if opener else {}
    base = V.pick_base(float(todo[0]["lat"]), float(todo[0]["lng"]), kid, key, **kw)
    print(f"  주소: {base}")
    buf, n, miss = [], 0, 0
    try:
        for t in todo:
            try:
                d = V.call(float(t["lat"]), float(t["lng"]), t["dest"], kid, key, base, **kw)
                if n == 0:
                    print("  첫 응답 모양:", str({k: d.get(k) for k in ("code", "message")}))
                r = V.parse(d)
            except V.Stop:
                raise
            except Exception as e:   # 한 건 실패는 넘어간다
                print(f"  {t['apt_seq']} {t['dest']}: {str(e)[:120]}")
                continue
            miss += r is None
            buf.append((t["apt_seq"], t["dest"], *(r or (None, None))))
            n += 1
            if len(buf) >= 200:
                save(db, buf); buf = []
            if not opener:
                V.pause(n)
    except V.Stop as e:
        print(f"  멈춤: {e}", file=sys.stderr)
        save(db, buf)
        return 2
    save(db, buf)
    print(f"  저장 {n:,}건 (경로 없음 {miss})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=3000)
    ap.add_argument("--refresh-days", type=int, default=120)
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.limit, a.refresh_days)
    except (DbError, V.Stop) as e:
        print(f"[drive] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
