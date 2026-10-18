"""C3 하락기 환금성·C4 거래 유지율 계산 (collector/liquidity.py, 0041). 한 번 계산하고, 다음 하락기가 오면 다시.

    python -m jobs.liquidity --archive gh          # Actions (보관 파일 = Releases raw-data)
    python -m jobs.liquidity --archive dir:<폴더>   # deals_YYYYMM.csv.gz 를 받아 둔 폴더

DB 는 R-ONE 주간 지수·K-apt 세대수를 읽고 complex_liquidity 를 통째로 바꾼다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from typing import Iterator
from zoneinfo import ZoneInfo

from collector.archive import asset_name, decode, open_store
from collector.db import Db, DbError, connect, lit, select
from collector.liquidity import SIDO, UP_START, Info, liquidity, region_windows, shift

KST = ZoneInfo("Asia/Seoul")
SIDO_CLS = {"11": 50008, "28": 50124, "41": 50016}   # R-ONE 서울·인천·경기 (인천은 50024 가 아니라 수도권 아래 50124 에 시계열이 있다)
COLS = ("apt_seq", "region_code", "households", "peak_m", "trough_m", "drop_pct", "window_src", "down_n",
        "down_turnover", "down_rank", "up_n", "up_turnover", "keep_ratio", "keep_rank")


def series(db: Db) -> dict[str, list[tuple[date, float]]]:
    rows = select(db, f"""
SELECT coalesce(r.region_code, s.sd) AS rc, r.cls_id, w.week_date::text AS d, w.value AS v
FROM rone_weekly w JOIN rone_regions r USING (cls_id)
LEFT JOIN (VALUES {', '.join(f"({c}, {lit(sd)})" for sd, c in SIDO_CLS.items())}) s(cls_id, sd) ON s.cls_id = r.cls_id
WHERE w.stat = 'sale' AND w.week_date BETWEEN DATE '2020-01-01' AND DATE '2023-12-31'
  AND (r.region_code IS NOT NULL OR s.sd IS NOT NULL)""")
    by: dict[tuple[str, int], list[tuple[date, float]]] = {}
    for r in rows:
        by.setdefault((r["rc"], r["cls_id"]), []).append((date.fromisoformat(r["d"]), float(r["v"])))
    out: dict[str, list[tuple[date, float]]] = {}
    for (rc, _), s in sorted(by.items(), key=lambda kv: min(kv[1])[0]):   # 같은 시군구에 지역이 여럿이면 가장 긴 시계열
        out.setdefault(rc, s)
    return out


def infos(db: Db) -> dict[str, Info]:
    rows = select(db, """
SELECT c.apt_seq, c.region_code, k.households, coalesce(k.use_date, make_date(c.build_year, 12, 31))::text AS ud
FROM complexes c JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
WHERE k.households > 0 AND left(c.region_code, 2) IN ('11', '28', '41')""")
    return {r["apt_seq"]: Info(r["region_code"], int(r["households"]), date.fromisoformat(r["ud"]) if r["ud"] else None)
            for r in rows}


def archive_rows(store, last_month: str, seen: list[int]) -> Iterator[dict]:
    """한 달 파일씩 흘려 읽는다(4년치를 한꺼번에 들고 있지 않게). seen[0] 에 읽은 행 수를 센다."""
    m = UP_START
    while m <= last_month:
        data = store.get(asset_name("deal", m))
        if data is None:
            raise FileNotFoundError(asset_name("deal", m))
        for r in decode(data):
            seen[0] += 1
            yield r
        m = shift(m, 1)


def run(db: Db, store, today: date) -> list[dict]:
    windows = region_windows(series(db))
    missing = [sd for sd in SIDO if sd not in windows]
    if missing:
        raise DbError(f"시도 하락 구간을 못 찾음: {missing}")
    seen = [0]
    out = liquidity(archive_rows(store, max(w.trough_m for w in windows.values()), seen), windows, infos(db))
    stmts = ["BEGIN;", "DELETE FROM complex_liquidity;"]
    for i in range(0, len(out), 500):
        vals = ", ".join("(" + ", ".join(lit(o[c]) for c in COLS) + f", {lit(today)})" for o in out[i:i + 500])
        stmts.append(f"INSERT INTO complex_liquidity ({', '.join(COLS)}, asof) VALUES {vals};")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    n_sgg = sum(1 for k, w in windows.items() if len(k) == 5)
    print(f"  하락 구간 시군구 {n_sgg}곳 + 시도 {len(SIDO)}곳, 보관 거래 {seen[0]:,}행 → 단지 {len(out):,}곳 "
          f"(C4 {sum(1 for o in out if o['keep_ratio'] is not None):,}곳)")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--archive", help="gh | dir:<폴더> (기본 HC_ARCHIVE)")
    a = ap.parse_args(argv)
    try:
        run(connect(a.db), open_store(a.archive), datetime.now(KST).date())
    except (DbError, FileNotFoundError) as e:
        print(f"[liquidity] 실패: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
