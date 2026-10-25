"""R-ONE 주간 지수 옛 구간을 DB 밖(Releases `rone_weekly_hist.csv.gz`)으로 옮긴다 (2026-10-25, DB 용량 397MB/500MB).

    python -m jobs.rone_archive --dry           # 옮길 행 수만
    python -m jobs.rone_archive --archive gh    # 보관 파일에 합쳐 올리고, 다시 읽어 확인한 뒤 DB 에서 지운다

옮기는 것: 2020-01-01 전 주, 서울(50008)·수도권(50002) 밖 지역. 화면·작업이 쓰는 범위는 DB 에 남는다
(시장 탭 장기 그래프·B4 백테스트 = 서울·수도권 전체, liquidity 2020~, market 30개월, balloon 2024-06~).
B1 백테스트(tools/analysis/backtest_b1.py)는 rone_all.json 덤프를 읽으므로 보관 파일 + DB 를 합쳐 만든다.
"""

from __future__ import annotations

import argparse
import sys

from collector.archive import decode, encode, open_store
from collector.db import Db, DbError, connect, select

ASSET = "rone_weekly_hist.csv.gz"
COLUMNS = ("stat", "cls_id", "week_id", "week_date", "value")
KEEP_CLS = (50008, 50002)
BEFORE = "2020-01-01"
WHERE = f"week_date < DATE '{BEFORE}' AND cls_id NOT IN ({', '.join(map(str, KEEP_CLS))})"


def rows_to_move(db: Db) -> list[dict]:
    out = []
    for y in range(2012, int(BEFORE[:4])):   # 한 번에 10만 행을 받지 않게 해마다
        out += select(db, f"SELECT stat, cls_id, week_id, week_date::text AS week_date, value FROM rone_weekly "
                          f"WHERE {WHERE} AND week_date >= DATE '{y}-01-01' AND week_date < DATE '{y + 1}-01-01'")
    return out


def merged(old: list[dict], new: list[dict]) -> list[dict]:
    """같은 (stat, cls_id, week_id) 는 새 값. 정렬해서 같은 내용이면 같은 파일."""
    by = {(r["stat"], str(r["cls_id"]), r["week_id"]): r for r in old}
    for r in new:
        by[(r["stat"], str(r["cls_id"]), r["week_id"])] = r
    return [by[k] for k in sorted(by, key=lambda k: (k[0], int(k[1]), k[2]))]


def run(db: Db, archive: str | None, dry: bool) -> int:
    new = rows_to_move(db)
    print(f"  옮길 행 {len(new):,}개({BEFORE} 전, 서울·수도권 밖)")
    if dry or not new:
        return 0
    store = open_store(archive)
    got = store.get(ASSET)
    old = decode(got) if got else []
    rows = merged(old, new)
    store.put(ASSET, encode(rows, COLUMNS))
    back = decode(store.get(ASSET) or b"")
    if len(back) != len(rows) or len(back) < len(new):
        print(f"  보관 파일 확인 실패({len(back):,}행) → DB 에서 안 지움", file=sys.stderr)
        return 1
    db.query(f"DELETE FROM rone_weekly WHERE {WHERE};")
    print(f"  보관 파일 {len(back):,}행 확인 → DB 에서 {len(new):,}행 지움(공간은 VACUUM FULL 뒤 돌아옴)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--archive", help="gh | dir:<폴더> (기본 HC_ARCHIVE)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), a.archive, a.dry)
    except DbError as e:
        print(f"[rone_archive] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
