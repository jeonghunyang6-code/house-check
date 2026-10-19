"""전월세 원본 보관과 요약 (docs/HANDOFF.md 0절 "저장 방식").

    # 과거 이력: API → 월별 원본 파일 + rent_monthly. DB 의 rents 에는 넣지 않는다. 이미 보관한 칸은 건너뛴다.
    python -m jobs.rent_archive backfill --regions seoul --months 202001-202508 --archive gh

    # 매일 (jobs.daily 다음): 일일 범위(당월·전월)를 벗어난 달을 DB → 원본 파일로 옮기고 DB 에서 지운다.
    #                        일일 범위의 달은 DB 의 rents 로 rent_monthly 를 다시 계산한다.
    python -m jobs.rent_archive daily --archive gh
    python -m jobs.rent_archive j24 --archive gh     # D3 2년 전 전세 중앙값(rent_j24)만 다시 계산
    python -m jobs.rent_archive roll --archive gh    # rent_monthly 에서 17개월 지난 달을 rentsum 파일로 옮기고 지운다(daily 에도 포함)
    python -m jobs.rent_archive sumhist --regions gyeonggi --months 202001-202505 --archive gh   # 원본 파일 → rentsum 파일 다시 만들기

요약 저장 구조(2026-10-19, 0053): rent_monthly(단지 × 면적군 × 달)는 최근 KEEP_MONTHS 달만 DB 에, 그 전은 시군구별
rentsum_<시군구>.csv.gz. 지역 합계(rent_region_month)는 전체 기간 DB. backfill 은 오래된 달 요약을 rentsum 파일로 바로 쓴다.
    #   이어서 해제 재확인: 2~11개월 전 한 달(jobs.daily.recheck_month)을 API 로 다시 받아 보관 파일과 맞춘다.
    #   전월세에는 해제 표시가 없어서, 늦게 들어온 신고는 새로 넣고(first_seen=오늘) 빠진 신고는 disappeared 로 둔다.
    #   마지막으로 D3 역전세용 24개월 전 ±1개월 전세 실제 중앙값(rent_j24)을 보관 파일 원본으로 다시 계산한다.

파일 업로드가 성공한 뒤에만 DB 를 바꾼다(요약·보관 기록·삭제를 트랜잭션 하나로). 업로드 후 DB 단계가 실패하면
다음 실행이 같은 달을 다시 처리한다(파일은 같은 내용으로 덮어쓴다).
종료 코드: 0 정상, 1 일부 실패, 2 호출 한도 초과로 중단.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import date, datetime
from statistics import median
from zoneinfo import ZoneInfo

from collector.archive import RENT_COLUMNS, Store, asset_name, decode, encode, merge, open_store
from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS, select_regions
from collector.rent_stats import rent_to_row, summarize
from collector.snapshot import keyed
from collector.sources.molit import ApiError, QuotaExceeded, fetch_rents
from jobs.daily import default_months, parse_months, recheck_month

KST = ZoneInfo("Asia/Seoul")
SUMMARY_COLUMNS = (
    "apt_seq", "area_group", "contract_month", "region_code", "apt_name", "n_jeonse", "jeonse_median_10k",
    "n_jeonse_new", "jeonse_new_median_10k", "n_jeonse_renew", "n_wolse", "wolse_deposit_median_10k",
    "wolse_rent_median_10k", "n_renewal_right_used", "n_type_blank",
)
REGION_COLUMNS = ("region_code", "contract_month", "n_jeonse", "n_jeonse_new", "n_jeonse_renew", "n_wolse")
CHUNK = 500
KEEP_MONTHS = 17   # rent_monthly 에 남기는 달 수(이번 달 포함). D4 전세 1년 변화가 16개월 전 달까지 본다(sql/metrics.sql 9)


def sum_cutoff(today: date) -> str:
    """이 달부터 rent_monthly 에 둔다. 그 전 달은 rentsum 파일."""
    y, m = today.year, today.month - (KEEP_MONTHS - 1)
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y}{m:02d}"


def sum_name(region: str) -> str:
    return f"rentsum_{region}.csv.gz"


def region_rows(sums: list[dict]) -> list[dict]:
    """단지 요약 → 시군구 × 달 합계 (rent_region_month)."""
    g: dict[tuple[str, str], dict] = {}
    for s in sums:
        r = g.setdefault((s["region_code"], s["contract_month"]), dict.fromkeys(REGION_COLUMNS[2:], 0))
        for c in REGION_COLUMNS[2:]:
            r[c] += int(s[c])
    return [{"region_code": rc, "contract_month": m, **v} for (rc, m), v in sorted(g.items())]


def summary_sql(month: str, regions: list[str], sums: list[dict], keep: bool = True) -> list[str]:
    """해당 (시군구들, 달)의 요약을 바꾸는 문장들 (트랜잭션 안에서 쓴다). sums = summarize(원본 행).
    지역 합계는 늘 쓰고, 단지 요약(rent_monthly)은 keep(최근 KEEP_MONTHS 달)일 때만."""
    rl = ", ".join(lit(r) for r in regions)
    stmts = [f"DELETE FROM rent_region_month WHERE contract_month = {lit(month)} AND region_code IN ({rl});"]
    rr = ["(" + ", ".join(lit(r[c]) for c in REGION_COLUMNS) + ")" for r in region_rows(sums)]
    if rr:
        stmts.append(f"INSERT INTO rent_region_month ({', '.join(REGION_COLUMNS)}) VALUES " + ", ".join(rr) + ";")
    if not keep:
        return stmts
    stmts.append(f"DELETE FROM rent_monthly WHERE contract_month = {lit(month)} AND region_code IN ({rl});")
    vals = ["(" + ", ".join(lit(s[c]) for c in SUMMARY_COLUMNS) + ")" for s in sums]
    for i in range(0, len(vals), CHUNK):
        stmts.append(f"INSERT INTO rent_monthly ({', '.join(SUMMARY_COLUMNS)}) VALUES\n" + ",\n".join(vals[i:i + CHUNK]) + ";")
    return stmts


def write_sums(store: Store, by_region: dict[str, list[dict]]) -> int:
    """시군구별 rentsum 파일에 요약 행을 넣는다. 넣는 행이 있는 달은 그 시군구 파일에서 통째로 바꾼다."""
    n = 0
    for rc, new in sorted(by_region.items()):
        months = {str(r["contract_month"]) for r in new}
        old = store.get(sum_name(rc))
        kept = [r for r in (decode(old) if old else []) if r["contract_month"] not in months]
        rows = kept + [{c: "" if r[c] is None else str(r[c]) for c in SUMMARY_COLUMNS} for r in new]
        rows.sort(key=lambda r: (r["contract_month"], r["apt_seq"], int(r["area_group"])))
        store.put(sum_name(rc), encode(rows, SUMMARY_COLUMNS))
        n += len(new)
    return n


def iter_sums(store: Store, regions: list[str], since: str = "000000"):
    """rentsum 파일들 → 요약 행(값은 문자열)을 하나씩. 파일이 없는 시군구는 건너뛴다(파일 하나씩만 메모리에)."""
    for rc in regions:
        data = store.get(sum_name(rc))
        if data:
            for r in decode(data):
                if r["contract_month"] >= since:
                    yield r


def archive_sql(month: str, counts: dict[str, int], source: str, today: date) -> str:
    vals = ", ".join(
        f"('rent', {lit(r)}, {lit(month)}, {n}, {lit(source)}, {lit(today)}, {lit(asset_name('rent', month))})"
        for r, n in counts.items()
    )
    return (
        "INSERT INTO archive_cells (kind, region_code, contract_month, n_rows, source, archived_at, asset_name) "
        f"VALUES {vals} ON CONFLICT (kind, region_code, contract_month) DO UPDATE SET n_rows = EXCLUDED.n_rows, "
        "source = EXCLUDED.source, archived_at = EXCLUDED.archived_at, asset_name = EXCLUDED.asset_name;"
    )


def write_file(store: Store, month: str, rows: list[dict], regions: set[str]) -> int:
    name = asset_name("rent", month)
    old = store.get(name)
    merged = merge(decode(old) if old else [], rows, regions)
    store.put(name, encode(merged))
    return len(merged)


def flush(db: Db, store: Store, month: str, rows: list[dict], counts: dict[str, int], source: str, today: date,
          extra_sql: list[str] = (), sink: dict[str, list[dict]] | None = None) -> int:
    """원본 파일 → DB(요약·보관 기록). 오래된 달(sum_cutoff 전)의 단지 요약은 DB 에 넣지 않고 sink(시군구별)에 모은다."""
    regions = sorted(counts)
    total = write_file(store, month, rows, set(regions))
    keep = month >= sum_cutoff(today)
    sums = summarize(rows)
    db.query("\n".join(["BEGIN;", *summary_sql(month, regions, sums, keep), archive_sql(month, counts, source, today),
                        *extra_sql, "COMMIT;"]))
    if not keep:
        if sink is None:
            write_sums(store, _by_region(sums))
        else:
            for k, v in _by_region(sums).items():
                sink.setdefault(k, []).extend(v)
    return total


def _by_region(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["region_code"], []).append(r)
    return out


def backfill(db: Db, store: Store, regions: list[str], months: list[str], today: date, fetch=fetch_rents) -> int:
    window_start = min(default_months(today))
    if max(months) >= window_start:
        raise SystemExit(f"backfill 은 일일 범위({window_start}~) 이전 달만 받는다. --months 를 줄일 것")
    done = {
        (r["region_code"], r["contract_month"])
        for r in select(db, "SELECT region_code, contract_month FROM archive_cells WHERE kind = 'rent' "
                            f"AND contract_month IN ({', '.join(lit(m) for m in months)})")
    }
    sink: dict[str, list[dict]] = {}   # 오래된 달 단지 요약 → 끝에 rentsum 파일로 한 번에
    try:
        return _backfill(db, store, regions, months, today, fetch, done, sink)
    finally:
        if sink:
            n = write_sums(store, sink)
            print(f"  전월세 요약 보관 파일: {len(sink)}개 시군구 {n:,}행")


def _backfill(db: Db, store: Store, regions: list[str], months: list[str], today: date, fetch, done: set, sink: dict) -> int:
    failures = 0
    for month in months:
        todo = [r for r in regions if (r, month) not in done]
        if not todo:
            continue
        rows: list[dict] = []
        counts: dict[str, int] = {}
        stop = False
        for code in todo:
            try:
                got = fetch(code, month)
            except QuotaExceeded as e:
                print(f"  전월세 {code} {REGIONS[code]} {month}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
                stop = True
                break
            except ApiError as e:
                failures += 1
                print(f"  전월세 {code} {REGIONS[code]} {month}: 실패 {e}", file=sys.stderr)
                continue
            rows += [rent_to_row(k, code, month, x) for k, x in keyed(got).items()]
            counts[code] = len(got)
        if counts:
            try:
                total = flush(db, store, month, rows, counts, "api_backfill", today, sink=sink)
                print(f"  전월세 {month}: {len(counts)}개 시군구 {len(rows)}건 보관 (파일 전체 {total}건)")
            except Exception as e:  # 파일·DB 단계 실패는 다음 실행에서 다시 받는다
                failures += 1
                print(f"  전월세 {month}: 보관 실패 {type(e).__name__}: {e}", file=sys.stderr)
        if len({r["contract_month"] for rs in sink.values() for r in rs}) >= 12:   # 중간에 끊겨도 남도록 12개월마다 파일로
            n = write_sums(store, sink)
            print(f"  전월세 요약 보관 파일: {len(sink)}개 시군구 {n:,}행")
            sink.clear()
        if stop:
            return 2
    return 1 if failures else 0


def _db_rows(db: Db, month: str) -> list[dict]:
    cols = ", ".join(
        f"{c}::text AS {c}" if c in ("contract_date", "term_start", "term_end", "first_seen_date", "last_seen_date")
        else c for c in RENT_COLUMNS
    )
    return select(db, f"SELECT {cols} FROM rents WHERE contract_month = {lit(month)}")


def daily(db: Db, store: Store, today: date) -> int:
    window = default_months(today)
    old = [r["m"] for r in select(
        db, f"SELECT DISTINCT contract_month AS m FROM rents WHERE contract_month < {lit(min(window))} ORDER BY 1")]
    failures = 0
    for month in old:
        try:
            rows = _db_rows(db, month)
            counts: dict[str, int] = {}
            for r in rows:
                counts[r["region_code"]] = counts.get(r["region_code"], 0) + 1
            delete = [
                f"DELETE FROM rent_events WHERE rent_key IN (SELECT rent_key FROM rents WHERE contract_month = {lit(month)});",
                f"DELETE FROM rents WHERE contract_month = {lit(month)};",
            ]
            total = flush(db, store, month, rows, counts, "db_rollover", today, delete)
            print(f"  전월세 {month}: DB → 파일 {len(rows)}건 (파일 전체 {total}건), DB 에서 삭제")
        except Exception as e:
            failures += 1
            print(f"  전월세 {month}: 이관 실패 {type(e).__name__}: {e}", file=sys.stderr)
    for month in window:
        try:
            rows = _db_rows(db, month)
            regions = sorted({r["region_code"] for r in rows})
            if regions:
                db.query("\n".join(["BEGIN;", *summary_sql(month, regions, summarize(rows)), "COMMIT;"]))
            print(f"  전월세 {month}: 요약 갱신 {len(rows)}건")
        except DbError as e:
            failures += 1
            print(f"  전월세 {month}: 요약 실패 {e}", file=sys.stderr)
    return 1 if failures else 0


def recheck_rows(old: list[dict], got: list, code: str, month: str, today: date) -> tuple[list[dict], int, int]:
    """한 시군구의 보관 행(old)을 다시 받은 API 결과(got)와 맞춘다. 있던 행은 처음 본 날을 유지한다.
    돌려주는 값: (새 행 목록, 늦게 들어온 건수, 빠진 건수)."""
    prev = {r["rent_key"]: r for r in old}
    new = keyed(got)
    out, added = [], 0
    for k, x in new.items():
        if k in prev:
            out.append({**prev[k], "last_seen_date": today.isoformat(), "disappeared": False})
        else:
            added += 1
            out.append(rent_to_row(k, code, month, x, today.isoformat(), today.isoformat()))
    gone = [r for k, r in prev.items() if k not in new]
    newly = sum(str(r.get("disappeared", "")).lower() not in ("1", "true") for r in gone)
    return out + [{**r, "disappeared": True} for r in gone], added, newly


def recheck(db: Db, store: Store, today: date, fetch=fetch_rents) -> int:
    month = recheck_month(today)
    data = store.get(asset_name("rent", month))
    if data is None:
        print(f"  전월세 재확인 {month}: 보관 파일 없음, 건너뜀")
        return 0
    by_region: dict[str, list[dict]] = {}
    for r in decode(data):
        by_region.setdefault(r["region_code"], []).append(r)
    rows: list[dict] = []
    counts: dict[str, int] = {}
    failures = added = gone = 0
    for code in sorted(by_region):
        try:
            got = fetch(code, month)
        except QuotaExceeded as e:
            print(f"  전월세 재확인 {code} {month}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
            return 2
        except ApiError as e:
            failures += 1
            print(f"  전월세 재확인 {code} {month}: 실패 {e}", file=sys.stderr)
            continue
        if not got:  # 빈 응답으로 한 시군구 전체를 지우지 않는다
            print(f"  전월세 재확인 {code} {month}: 0건 응답, 기존 유지", file=sys.stderr)
            continue
        rs, a, g = recheck_rows(by_region[code], got, code, month, today)
        rows += rs
        counts[code] = len(rs)
        added, gone = added + a, gone + g
    if counts:
        try:
            flush(db, store, month, rows, counts, "recheck", today)
        except Exception as e:
            print(f"  전월세 재확인 {month}: 보관 실패 {type(e).__name__}: {e}", file=sys.stderr)
            return 1
    print(f"  전월세 재확인 {month}: {len(counts)}개 시군구, 늦은 신고 {added}건, 사라짐 {gone}건")
    return 1 if failures else 0


def roll_sums(db: Db, store: Store, today: date) -> int:
    """rent_monthly 에서 sum_cutoff 전 달을 rentsum 파일로 옮기고 DB 에서 지운다. 파일을 다시 받아 행 수를 맞춘 뒤에만 지운다."""
    cut = sum_cutoff(today)
    months = [r["m"] for r in select(db, f"SELECT DISTINCT contract_month AS m FROM rent_monthly WHERE contract_month < {lit(cut)} ORDER BY 1")]
    if not months:
        return 0
    old = []   # 달마다 읽는다(2026-10-19 처음 옮길 때 68만 행을 한 번에 읽다 psql 5분 제한에 걸렸다)
    for m in months:
        old += select(db, f"SELECT {', '.join(SUMMARY_COLUMNS)} FROM rent_monthly WHERE contract_month = {lit(m)}")
    by = _by_region(old)
    write_sums(store, by)
    for rc, rs in by.items():
        months, data = {r["contract_month"] for r in rs}, store.get(sum_name(rc))
        back = sum(1 for r in decode(data) if r["contract_month"] in months) if data else -1
        if back != len(rs):
            print(f"  전월세 요약 {rc}: 파일 {back}행 ≠ DB {len(rs)}행, 지우지 않음", file=sys.stderr)
            return 1
    db.query(f"DELETE FROM rent_monthly WHERE contract_month < {lit(cut)};")
    if len(old) > 50_000:   # 처음 옮길 때처럼 많이 지웠으면 빈 공간을 돌려준다(DELETE 만으로는 DB 크기가 안 준다)
        db.query("VACUUM FULL rent_monthly;")
    print(f"  전월세 요약 {min(r['contract_month'] for r in old)}~{max(r['contract_month'] for r in old)}: "
          f"{len(by)}개 시군구 {len(old):,}행 → rentsum 파일, DB 에서 삭제 ({cut}~ 만 남김)")
    return 0


def sumhist(store: Store, regions: list[str], months: list[str]) -> int:
    """원본 월별 파일 → rentsum 파일 (그 시군구·달을 다시 만든다). DB 는 쓰지 않는다."""
    want, sink, miss = set(regions), {}, []
    for m in months:
        data = store.get(asset_name("rent", m))
        if data is None:
            miss.append(m)
            continue
        for k, v in _by_region(summarize([r for r in decode(data) if r["region_code"] in want])).items():
            sink.setdefault(k, []).extend(v)
    n = write_sums(store, sink)
    print(f"  rentsum: {len(sink)}개 시군구 {n:,}행 ({months[0]}~{months[-1]})" + (f", 원본 없음 {miss}" if miss else ""))
    return 0


def j24_months(today: date) -> list[str]:
    """D3: 24개월 전 ±1개월 (sql/metrics.sql j24 와 같은 달들)."""
    out = []
    for k in (25, 24, 23):
        y, m = today.year, today.month - k
        while m < 1:
            y, m = y - 1, m + 12
        out.append(f"{y}{m:02d}")
    return out


def j24_rows(rows: list[dict]) -> list[dict]:
    """보관 파일 원본 → 단지 × 면적군 전세(신규·갱신 모두) 보증금 실제 중앙값. 사라진 신고는 뺀다."""
    g: dict[tuple[str, int], list[int]] = {}
    for r in rows:
        if str(r.get("disappeared", "")).lower() in ("1", "true") or int(r["monthly_rent_10k"]) != 0:
            continue
        g.setdefault((r["apt_seq"], math.floor(float(r["area_m2"]))), []).append(int(r["deposit_10k"]))
    return [{"apt_seq": a, "area_group": ag, "n": len(v), "median_10k": int(round(median(v)))}
            for (a, ag), v in sorted(g.items())]


def refresh_j24(db: Db, store: Store, today: date) -> int:
    months = j24_months(today)
    rows: list[dict] = []
    for m in months:
        data = store.get(asset_name("rent", m))
        if data is None:
            print(f"  D3 2년 전 전세: {m} 보관 파일 없음, 건너뜀")
            return 0
        rows += decode(data)
    out = j24_rows(rows)
    vals = [f"({lit(r['apt_seq'])}, {r['area_group']}, {lit(months[0])}, {lit(months[-1])}, {r['n']}, {r['median_10k']})"
            for r in out]
    stmts = ["BEGIN;", "DELETE FROM rent_j24;"]
    for i in range(0, len(vals), CHUNK):
        stmts.append("INSERT INTO rent_j24 (apt_seq, area_group, from_month, to_month, n, median_10k) VALUES\n"
                     + ",\n".join(vals[i:i + CHUNK]) + ";")
    try:
        db.query("\n".join([*stmts, "COMMIT;"]))
    except DbError as e:
        print(f"  D3 2년 전 전세: 저장 실패 {e}", file=sys.stderr)
        return 1
    print(f"  D3 2년 전 전세 {months[0]}~{months[-1]}: 원본 {len(rows):,}건 → {len(out):,}개 단지·면적군")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["backfill", "daily", "j24", "roll", "sumhist"])
    ap.add_argument("--regions", default="seoul")
    ap.add_argument("--months", help="backfill 용. 예: 202001-202508")
    ap.add_argument("--archive", help="gh | gh:<tag> | dir:<경로>. 기본 HC_ARCHIVE 또는 dir:data/archive")
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--no-recheck", action="store_true", help="daily 에서 지난달 재확인을 건너뛴다")
    ap.add_argument("--today", help="테스트용 기준일 YYYY-MM-DD")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else datetime.now(KST).date()
    db, store = connect(a.db), open_store(a.archive)
    t0 = time.monotonic()
    if a.mode == "backfill":
        if not a.months:
            ap.error("backfill 에는 --months 가 필요하다")
        rc = backfill(db, store, select_regions(a.regions), parse_months(a.months), today)
    elif a.mode == "j24":
        rc = refresh_j24(db, store, today)
    elif a.mode == "roll":
        rc = roll_sums(db, store, today)
    elif a.mode == "sumhist":
        if not a.months:
            ap.error("sumhist 에는 --months 가 필요하다")
        rc = sumhist(store, select_regions(a.regions), parse_months(a.months))
    else:
        rc = daily(db, store, today)
        if not a.no_recheck:
            rc = max(rc, recheck(db, store, today))
        rc = max(rc, refresh_j24(db, store, today))
        try:   # 요약 옮기기가 실패해도 매일 수집의 다른 결과는 그대로 두고 다음 날 다시 한다
            rc = max(rc, roll_sums(db, store, today))
        except Exception as e:
            print(f"  전월세 요약 옮기기 실패 {type(e).__name__}: {e}", file=sys.stderr)
            rc = max(rc, 1)
    print(f"[rent_archive] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
