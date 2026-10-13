"""매매 원본 보관 (저장 구조 C, 2026-10-14). 무료 플랜 DB 500MB 를 넘어 읽기 전용이 돼서,
오래된 매매 원본을 GitHub Releases 의 월별 CSV.gz (`deals_YYYYMM.csv.gz`) 로 옮기고 DB 에는 최근 2년만 둔다.

    python -m jobs.deal_archive export --months 202001-202409 --archive gh   # DB → 파일 (DB 는 읽기만)
    python -m jobs.deal_archive anchor --months 202001-202409 --archive gh   # 파일 → 과거 고정값 파일 (DB 안 씀)
    python -m jobs.deal_archive load --archive gh                            # 고정값 파일 → deal_anchor·deal_region_month (DB 씀)
    python -m jobs.deal_archive prune --before 202410                        # DB 에서 보관한 달을 지운다 (사용자 확인 뒤)
    python -m jobs.deal_archive roll --archive gh                            # 매일: 2년 지난 달을 보관 → 고정값 갱신 → DB 에서 뺀다

파일 하나 = 계약월 1개 × 수도권 전체 시군구. 올린 뒤 다시 내려받아 행 수를 DB 와 맞춰 본다.
DB 에서 지우는 단계는 따로(사용자 확인 뒤) 둔다. 종료 코드: 0 정상, 1 불일치·실패.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.archive import asset_name, decode, encode, open_store
from collector.deal_anchor import ANCHOR_COLUMNS, REGION_MONTH_COLUMNS, anchors, region_months
from collector.db import Db, DbError, connect, lit, select
from collector.regions import select_regions
from jobs.daily import parse_months

KST = ZoneInfo("Asia/Seoul")
DEAL_COLUMNS = (
    "deal_key", "apt_seq", "apt_name", "region_code", "contract_month", "contract_date", "area_m2", "floor",
    "price_10k", "deal_type", "is_cancelled", "cancel_date", "rgst_date", "first_seen_date", "last_seen_date",
    "disappeared", "prev_high_10k",
)


def month_rows(db: Db, month: str, regions: list[str]) -> list[dict]:
    # ORDER BY 없이 읽는다(디스크가 꽉 찼을 때 정렬 임시 파일을 못 쓴다). 정렬은 여기서
    rows = select(db, f"SELECT {', '.join(DEAL_COLUMNS)} FROM deals WHERE contract_month = {lit(month)} "
                      f"AND region_code IN ({', '.join(lit(r) for r in regions)})")
    return sorted(rows, key=lambda r: (r["region_code"], r["deal_key"]))


def run_export(db: Db, store, months: list[str], regions: list[str]) -> int:
    bad = 0
    for m in months:
        t = time.time()
        rows = month_rows(db, m, regions)
        name = asset_name("deal", m)
        store.put(name, encode(rows, DEAL_COLUMNS))
        back = store.get(name)
        n_back = len(decode(back)) if back else -1
        ok = n_back == len(rows)
        bad += not ok
        print(f"  {name}: DB {len(rows):,}행 → 파일 {n_back:,}행 {'확인' if ok else '불일치'} ({time.time() - t:.0f}초)")
    return 1 if bad else 0


def run_anchor(store, months: list[str]) -> int:
    rows: list[dict] = []
    for m in months:
        data = store.get(asset_name("deal", m))
        if data is None:
            print(f"  {asset_name('deal', m)} 없음 (export 먼저)", file=sys.stderr)
            return 1
        rows += decode(data)
    a, rm = anchors(rows), region_months(rows)
    store.put("deal_anchor.csv.gz", encode(a, ANCHOR_COLUMNS))
    store.put("deal_region_month.csv.gz", encode(rm, REGION_MONTH_COLUMNS))
    print(f"  보관 {len(rows):,}행 → deal_anchor {len(a):,}행 (전고점 구간 {sum(1 for x in a if x['peak_10k']):,}), "
          f"deal_region_month {len(rm):,}행 ({months[0]}~{months[-1]})")
    return 0


READ_WRITE = "SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE;"   # Supabase 읽기 전용(용량 초과) 중 정리용, 세션 한정


def load_sql(anchor_rows: list[dict], region_rows: list[dict]) -> str:
    def ins(table: str, cols: tuple[str, ...], rows: list[dict]) -> list[str]:
        out = []
        for i in range(0, len(rows), 1000):
            vals = ",\n".join("(" + ", ".join("NULL" if r[c] == "" else lit(r[c]) for c in cols) + ")" for r in rows[i:i + 1000])
            out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals};")
        return out
    return "\n".join([READ_WRITE, "BEGIN;", "TRUNCATE deal_anchor, deal_region_month;",
                      *ins("deal_anchor", ANCHOR_COLUMNS, anchor_rows),
                      *ins("deal_region_month", REGION_MONTH_COLUMNS, region_rows), "COMMIT;"])


def prune_sql(before: str) -> list[str]:
    """보관한 달(< before)을 DB 에서 뺀다. DELETE 로는 파일이 줄지 않아(무료 플랜 DB 크기 기준) 남길 행만 새 표로 옮겨 바꾼다.
    단계마다 따로 실행한다(앞 단계가 공간을 비워야 다음 단계가 쓸 자리가 생긴다)."""
    cols = ", ".join(c for c in DEAL_COLUMNS)    # area_group 은 생성 열이라 뺀다
    b = lit(before)
    return [
        # 1) 보조 색인부터 지워 공간을 비운다 (다시 만든다)
        READ_WRITE + "\nDROP INDEX IF EXISTS deals_complex_idx, deals_region_month_idx, deals_first_seen_idx;",
        # 2) 남길 행만 새 표로, 바꿔 끼우기
        READ_WRITE + f"""
BEGIN;
CREATE TABLE deals_keep (LIKE deals INCLUDING DEFAULTS INCLUDING GENERATED INCLUDING CONSTRAINTS);
INSERT INTO deals_keep ({cols}) SELECT {cols} FROM deals WHERE contract_month >= {b};
ALTER TABLE deal_events DROP CONSTRAINT IF EXISTS deal_events_deal_key_fkey;
DELETE FROM deal_events e WHERE NOT EXISTS (SELECT 1 FROM deals_keep k WHERE k.deal_key = e.deal_key);
DROP TABLE deals;
ALTER TABLE deals_keep RENAME TO deals;
ALTER TABLE deals ADD CONSTRAINT deals_pkey PRIMARY KEY (deal_key);
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_events ADD CONSTRAINT deal_events_deal_key_fkey FOREIGN KEY (deal_key) REFERENCES deals (deal_key);
COMMIT;""",
        # 3) 색인 다시 (0001)
        READ_WRITE + """
CREATE INDEX IF NOT EXISTS deals_complex_idx ON deals (apt_seq, area_group, contract_date);
CREATE INDEX IF NOT EXISTS deals_region_month_idx ON deals (region_code, contract_month);
CREATE INDEX IF NOT EXISTS deals_first_seen_idx ON deals (first_seen_date);""",
    ]


def run_load(db: Db, store) -> int:
    a, rm = store.get("deal_anchor.csv.gz"), store.get("deal_region_month.csv.gz")
    if a is None or rm is None:
        print("  deal_anchor·deal_region_month 파일 없음 (anchor 먼저)", file=sys.stderr)
        return 1
    a, rm = decode(a), decode(rm)
    db.query(load_sql(a, rm))
    n = select(db, "SELECT (SELECT count(*) FROM deal_anchor) AS a, (SELECT count(*) FROM deal_region_month) AS r")[0]
    print(f"  deal_anchor {n['a']:,}행 (파일 {len(a):,}), deal_region_month {n['r']:,}행 (파일 {len(rm):,})")
    return 0 if (n["a"], n["r"]) == (len(a), len(rm)) else 1


def run_prune(db: Db, store, before: str) -> int:
    # 지우기 전 확인: before 이전 달이 모두 보관돼 있고 행 수가 DB 와 같아야 한다
    months = [r["m"] for r in select(db, f"SELECT DISTINCT contract_month AS m FROM deals WHERE contract_month < {lit(before)}")]
    for m in sorted(months):
        data = store.get(asset_name("deal", m))
        n_db = select(db, f"SELECT count(*) AS n FROM deals WHERE contract_month = {lit(m)}")[0]["n"]
        n_file = len(decode(data)) if data else -1
        if n_db != n_file:
            print(f"  {m}: DB {n_db:,}행 ≠ 보관 {n_file:,}행 → 지우지 않고 멈춤", file=sys.stderr)
            return 1
    print(f"  보관 확인 {len(months)}개월, 지우기 시작")
    if not select(db, "SELECT count(*) AS n FROM deal_anchor")[0]["n"]:
        print("  deal_anchor 가 비어 있음 (load 먼저)", file=sys.stderr)
        return 1
    for i, q in enumerate(prune_sql(before), 1):
        t = time.time()
        db.query(q)
        print(f"  단계 {i}/3 ({time.time() - t:.0f}초)")
    n = select(db, "SELECT count(*) AS n, min(contract_month) AS m, pg_database_size(current_database()) / 1000000 AS mb FROM deals")[0]
    print(f"  남은 매매 {n['n']:,}행 ({n['m']}~), DB {n['mb']}MB")
    return 0


KEEP_MONTHS = 24   # DB 에 남기는 기간: 이번 달 포함 25개월 (2026-10 → 202410~)


def cutoff(today: date) -> str:
    """이 계약월보다 이전은 DB 밖(보관 파일)."""
    y, m = today.year - KEEP_MONTHS // 12, today.month - KEEP_MONTHS % 12
    if m < 1:
        y, m = y - 1, m + 12
    return f"{y}{m:02d}"


def roll_sql(month: str, region_rows: list[dict]) -> str:
    """보관 파일을 올린 뒤 한 트랜잭션: 역대 최고 갱신, 월별 거래 수 추가, DB 에서 삭제."""
    m = lit(month)
    vals = ",\n".join("(" + ", ".join("NULL" if r[c] == "" else lit(r[c]) for c in REGION_MONTH_COLUMNS) + ")" for r in region_rows)
    return "\n".join([READ_WRITE, "BEGIN;", f"""
INSERT INTO deal_anchor (apt_seq, area_group, hist_high_10k, hist_high_date)
SELECT DISTINCT ON (apt_seq, area_group) apt_seq, area_group, price_10k, contract_date FROM deals
WHERE contract_month = {m} AND NOT is_cancelled AND deal_type = '중개'
ORDER BY apt_seq, area_group, price_10k DESC, contract_date
ON CONFLICT (apt_seq, area_group) DO UPDATE SET hist_high_10k = EXCLUDED.hist_high_10k, hist_high_date = EXCLUDED.hist_high_date
WHERE EXCLUDED.hist_high_10k > deal_anchor.hist_high_10k;""",
        (f"INSERT INTO deal_region_month ({', '.join(REGION_MONTH_COLUMNS)}) VALUES\n{vals}\n"
         "ON CONFLICT (region_code, contract_month) DO UPDATE SET " +
         ", ".join(f"{c} = EXCLUDED.{c}" for c in REGION_MONTH_COLUMNS[2:]) + ";") if region_rows else "",
        f"DELETE FROM deal_events e USING deals d WHERE e.deal_key = d.deal_key AND d.contract_month = {m};",
        f"DELETE FROM deals WHERE contract_month = {m};",
        "COMMIT;"])


def run_roll(db: Db, store, regions: list[str], today: date) -> int:
    if not select(db, "SELECT to_regclass('deal_anchor') IS NOT NULL AND EXISTS (SELECT 1 FROM deal_anchor) AS ok")[0]["ok"]:
        print("  deal_anchor 가 비어 있음: 저장 구조 C 설정(load·prune) 전이라 건너뜀")
        return 0
    cut = cutoff(today)
    months = sorted(r["m"] for r in select(db, f"SELECT DISTINCT contract_month AS m FROM deals WHERE contract_month < {lit(cut)}"))
    if not months:
        print(f"  {cut} 이전 달 없음")
        return 0
    for m in months:
        rows = month_rows(db, m, regions)
        name = asset_name("deal", m)
        store.put(name, encode(rows, DEAL_COLUMNS))
        back = store.get(name)
        back_rows = decode(back) if back else []
        if len(back_rows) != len(rows):
            print(f"  {name}: DB {len(rows):,}행 ≠ 파일 {len(back_rows):,}행 → DB 는 그대로 둠", file=sys.stderr)
            return 1
        db.query(roll_sql(m, region_months(back_rows)))
        print(f"  {m}: {len(rows):,}행 보관 → 역대 최고·월별 거래 수 갱신 → DB 에서 뺌")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["export", "anchor", "load", "prune", "roll"])
    ap.add_argument("--months")
    ap.add_argument("--before", help="prune: 이 계약월 이전을 지운다 (YYYYMM)")
    ap.add_argument("--regions", default="sudogwon")
    ap.add_argument("--archive")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    print(f"[deal_archive] {a.step} {a.months} {datetime.now(KST):%Y-%m-%d %H:%M}")
    try:
        if a.step == "anchor":
            return run_anchor(open_store(a.archive), parse_months(a.months))
        if a.step == "load":
            return run_load(connect(a.db), open_store(a.archive))
        if a.step == "roll":
            return run_roll(connect(a.db), open_store(a.archive), select_regions(a.regions), datetime.now(KST).date())
        if a.step == "prune":
            return run_prune(connect(a.db), open_store(a.archive), a.before)
        return run_export(connect(a.db), open_store(a.archive), parse_months(a.months), select_regions(a.regions))
    except DbError as e:
        print(f"[deal_archive] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
