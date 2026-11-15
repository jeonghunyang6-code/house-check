"""재건축·리모델링 단계 자동 갱신 (collector/remodel.py → remodel_auto 0086). daily.yml 이 jobs.complex_news 바로 뒤에 돈다.

관심·내 단지의 제목 기사(complex_news, 최근 30일)에서 손 관리 단계(REMODELS)·이미 올린 자동 단계보다 앞선 단계를 찾으면 넣는다.
'빼줘'로 지운(removed) 단계는 다시 넣지 않는다. 규칙만(AI 없음).

    python -m jobs.remodel [--db api]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from collector import remodel as R
from collector.db import Db, DbError, connect, lit, select

DAYS = 30


def passed(seq: str, auto: list[dict]) -> int:
    """이미 지난 단계 번호: 손 관리 + 자동(빼지 않은 것) 중 가장 앞. 없으면 -1."""
    hand = [R.idx(s.stage) for s in R.REMODELS[seq].steps] if seq in R.REMODELS else []
    got = [R.idx(a["stage"]) for a in auto if a["apt_seq"] == seq and a["status"] == "auto"]
    return max(hand + got, default=-1)


def run(db: Db) -> int:
    rows = select(db, f"SELECT apt_seq, title, outlet, url, pub::text pub FROM complex_news WHERE in_title AND pub >= current_date - {DAYS}")
    auto = select(db, "SELECT apt_seq, stage, status FROM remodel_auto")
    gone = {(a["apt_seq"], a["stage"]) for a in auto if a["status"] != "auto"}
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["apt_seq"], []).append({**r, "pub": date.fromisoformat(r["pub"])})
    new = []
    for seq, rs in by.items():
        for c in R.detect(rs, passed(seq, auto)):
            if (seq, c["stage"]) in gone:
                continue
            new.append(f"({lit(seq)}, {lit(c['stage'])}, {lit(c['first'])}, {len(c['press'])}, {lit(','.join(c['press']))}, "
                       f"{lit(json.dumps(c['urls'], ensure_ascii=False))}::jsonb)")
            print(f"  {seq}: {c['stage']} (언론사 {len(c['press'])}곳, {c['first']})")
    if new:
        db.query("INSERT INTO remodel_auto (apt_seq, stage, first_date, n_press, press, urls) VALUES " + ", ".join(new)
                 + " ON CONFLICT (apt_seq, stage) DO NOTHING;")
    print(f"  제목 기사 {len(rows)}건(최근 {DAYS}일) → 새 단계 {len(new)}건")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db))
    except DbError as e:
        print(f"[remodel] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
