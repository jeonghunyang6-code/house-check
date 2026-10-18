"""E6 갈아타기 목표 후보 계산 (collector/gap.py → e6_targets, 0049). 분기가 바뀔 때 의미가 있어 매주 돌려도 결과는 분기마다 바뀐다.

    python -m jobs.gap --archive gh            # Actions (보관 파일 = Releases raw-data)
    python -m jobs.gap --archive dir:<폴더>     # deals_YYYYMM.csv.gz 를 받아 둔 폴더

20분기 중 2년 넘은 앞부분은 보관 파일(deals_YYYYMM), 나머지는 DB deals.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.archive import asset_name, decode, open_store
from collector.db import Db, DbError, connect, lit, select
from collector.gap import quarter_medians, quarters, targets

KST = ZoneInfo("Asia/Seoul")
COLS = ("apt_seq", "rank", "target_seq", "ratio_now", "gap_now_10k", "gap_pct", "n_q", "dist_m")


def _months(qs: list[str]) -> list[str]:
    out = []
    for q in qs:
        y, n = int(q[:4]), int(q[-1])
        out += [f"{y}{m:02d}" for m in range(3 * n - 2, 3 * n + 1)]
    return out


def series(db: Db, store, qs: list[str]) -> dict[str, dict[str, float]]:
    db_first = select(db, "SELECT min(contract_month) AS m FROM deals")[0]["m"]
    # 보관 파일과 DB 에 걸친 분기(매달 roll 로 경계가 움직인다)와 보관 분기는 원본 행을 모아 분기 중앙값을 낸다(달별 중앙값끼리는 합칠 수 없다)
    db_q = {q for q in qs if all(m >= db_first for m in _months([q]))}
    rows = []
    for m in [m for m in _months(qs) if m < db_first]:
        data = store.get(asset_name("deal", m))
        if data is None:
            raise FileNotFoundError(asset_name("deal", m))
        rows += decode(data)
    mixed_m = [m for q in qs if q not in db_q for m in _months([q]) if m >= db_first]
    if mixed_m:
        rows += [{k: ("" if v is None else str(v)) for k, v in r.items()} for r in select(db, f"""SELECT apt_seq, contract_month, area_m2,
            floor, deal_type, CASE WHEN is_cancelled THEN '1' ELSE '0' END AS is_cancelled, price_10k FROM deals
            WHERE contract_month IN ({', '.join(lit(m) for m in mixed_m)}) AND area_group IN (84, 85)""")]
    out = quarter_medians(rows, qs)
    for r in select(db, f"""SELECT apt_seq, substr(contract_month, 1, 4) || 'Q' || ((substr(contract_month, 5, 2)::int - 1) / 3 + 1) AS q,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) AS p FROM deals
            WHERE NOT is_cancelled AND deal_type = '중개' AND floor IS DISTINCT FROM 1 AND area_group IN (84, 85)
              AND contract_month >= {lit(db_first)} AND contract_month <= {lit(_months([qs[-1]])[-1])} GROUP BY 1, 2"""):
        if r["q"] in db_q:
            out.setdefault(r["apt_seq"], {})[r["q"]] = float(r["p"])
    return out


def run(db: Db, store, today: date) -> int:
    qs = quarters(today)
    ser = series(db, store, qs)
    coords = {r["apt_seq"]: (float(r["lat"]), float(r["lng"])) for r in select(db, "SELECT apt_seq, lat, lng FROM complexes WHERE lat IS NOT NULL")}
    out = targets(ser, coords, qs)
    stmts = ["BEGIN;", "DELETE FROM e6_targets;"]
    for i in range(0, len(out), 1000):
        stmts.append(f"INSERT INTO e6_targets ({', '.join(COLS)}, last_q, asof) VALUES "
                     + ", ".join("(" + ", ".join(lit(o[c]) for c in COLS) + f", {lit(qs[-1])}, {lit(today)})" for o in out[i:i + 1000]) + ";")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    print(f"  분기 {qs[0]}~{qs[-1]}, 분기 가격 있는 단지 {len(ser):,}곳 → 목표 후보가 있는 단지 {len({o['apt_seq'] for o in out}):,}곳, {len(out):,}행")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--archive", help="gh | dir:<폴더> (기본 HC_ARCHIVE)")
    a = ap.parse_args(argv)
    try:
        return run(connect(a.db), open_store(a.archive), datetime.now(KST).date())
    except (DbError, FileNotFoundError) as e:
        print(f"[gap] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
