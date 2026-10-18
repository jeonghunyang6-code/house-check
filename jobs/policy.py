"""규제 이력 적재 (collector/policy.py → policy_zone·policy_events, 0043). 원본이 코드라 바꿀 때마다 한 번 돌린다.

    python -m jobs.policy
"""

from __future__ import annotations

import argparse
import sys

from collector.db import DbError, connect, lit
from collector.policy import EVENTS, ZONES


def statements() -> str:
    zv = [f"({lit(z.kind)}, {lit(c)}, {lit(u)}, {lit(z.start)}, {lit(z.end)}, {lit(z.scope)}, {lit(z.note)}, {lit(z.source)})"
          for z in ZONES for c in z.region_codes for u in (z.umd_names or (None,))]
    ev = [f"({lit(d)}, {lit(k)}, {lit(t)}, {lit(s)})" for d, k, t, s in EVENTS]
    return "\n".join([
        "BEGIN;", "DELETE FROM policy_zone;", "DELETE FROM policy_events;",
        "INSERT INTO policy_zone (kind, region_code, umd_name, start_date, end_date, scope, note, source) VALUES " + ", ".join(zv) + ";",
        "INSERT INTO policy_events (event_date, kind, title, source) VALUES " + ", ".join(ev) + ";",
        "COMMIT;"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        connect(a.db).query(statements())
    except DbError as e:
        print(f"[policy] 실패: {e}", file=sys.stderr)
        return 1
    print(f"  규제 이력: 구역 {sum(len(z.region_codes) * len(z.umd_names or (None,)) for z in ZONES)}행, 사건 {len(EVENTS)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
