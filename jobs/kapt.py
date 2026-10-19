"""K-apt 단지 정보 수집과 실거래 단지 연결 (collector/kapt.py, 0008).

    python -m jobs.kapt complexes --regions seoul --months 202001-202608  # 과거 실거래에서 단지 속성 채우기
    python -m jobs.kapt list --regions sudogwon                           # K-apt 단지 목록
    python -m jobs.kapt info --limit 3000                                 # 기본 정보 (아직 안 받은 단지만)
    python -m jobs.kapt detail --limit 3000                               # 상세 정보: 역·도보 시간·주차 (실거래 연결 단지만, 0021)
    python -m jobs.kapt match --regions sudogwon                          # 연결

매일 수집(jobs.daily)이 그날 받은 매매의 단지 속성을 complexes 에 넣으므로, complexes 모드는
그 이전 이력에 있는 단지를 채우는 1회용이다. 시군구마다 deals 에 있는 단지가 모두 채워지면 거기서 멈춘다.
호출 한도 초과(QuotaExceeded)면 종료 코드 2 로 멈추고, 다시 실행하면 이어서 한다.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.kapt import detail_row, fetch_detail, fetch_info, fetch_list, info_row, match_complexes
from collector.pg_store import complexes_sql
from collector.regions import REGIONS, select_regions
from collector.sources.molit import ApiError, QuotaExceeded, fetch_trades
from jobs.daily import parse_months

KST = ZoneInfo("Asia/Seoul")
# 2026-10-13: 서버가 "HTTP_ERROR" 본문만 3,377번 연달아 돌려줬는데 작업은 끝까지 호출을 계속했다(한 시간 가까이 헛호출).
# 연속 실패가 FAIL_STREAK 번이면 PAUSES 초씩 쉬고 같은 단지부터 다시 부른다. 쉬고 나서도 계속 실패하면 멈춘다(rc 2, 다음 실행이 이어서 한다)
FAIL_STREAK = 20
PAUSES = (60, 300, 900)
INFO_COLS = ("addr", "road_addr", "households", "use_date", "dong_cnt", "top_floor", "builder", "heat_type",
             "sale_type", "hh_lt60", "hh_60_85", "hh_85_135", "hh_gt135")
DETAIL_COLS = ("subway_line", "subway_station", "walk_subway", "walk_bus", "parking_ground", "parking_under", "ev_charger",
               "cctv", "welfare")


def run_complexes(db: Db, regions: list[str], months: list[str], today: date) -> int:
    for code in regions:
        missing = select(db, "SELECT count(DISTINCT d.apt_seq) AS n FROM deals d LEFT JOIN complexes c USING (apt_seq) "
                             f"WHERE d.region_code = {lit(code)} AND c.apt_seq IS NULL")[0]["n"]
        for ym in sorted(months, reverse=True):  # 최근 달부터: 대부분의 단지가 먼저 잡힌다
            if missing == 0:
                break
            try:
                rows = fetch_trades(code, ym)
            except QuotaExceeded as e:
                print(f"  {code} {ym}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
                return 2
            except ApiError as e:
                print(f"  {code} {ym}: 실패 {e}", file=sys.stderr)
                continue
            sql = complexes_sql(rows, today)
            if sql:
                db.query(sql)
            missing = select(db, "SELECT count(DISTINCT d.apt_seq) AS n FROM deals d LEFT JOIN complexes c USING (apt_seq) "
                                 f"WHERE d.region_code = {lit(code)} AND c.apt_seq IS NULL")[0]["n"]
        print(f"  {code} {REGIONS[code]}: 속성 없는 단지 {missing}개")
    return 0


def run_list(db: Db, regions: list[str], today: date) -> int:
    rc = 0
    for code in regions:
        try:
            items = fetch_list(code)
        except QuotaExceeded as e:
            print(f"  {code}: 호출 한도 초과로 중단: {e}", file=sys.stderr)
            return 2
        except ApiError as e:
            print(f"  {code} {REGIONS[code]}: 실패 {e}", file=sys.stderr)
            rc = 1
            continue
        if items:
            vals = ", ".join(f"({lit(i['kaptCode'])}, {lit(i['kaptName'])}, {lit(code)}, {lit(i.get('bjdCode'))}, {lit(today)})"
                             for i in items)
            db.query("INSERT INTO kapt_complexes (kapt_code, kapt_name, region_code, bjd_code, listed_at) "
                     f"VALUES {vals} ON CONFLICT (kapt_code) DO UPDATE SET kapt_name = EXCLUDED.kapt_name, "
                     "region_code = EXCLUDED.region_code, bjd_code = EXCLUDED.bjd_code, listed_at = EXCLUDED.listed_at;")
        print(f"  {code} {REGIONS[code]}: K-apt 단지 {len(items)}개")
    return rc


def run_info(db: Db, limit: int, today: date, sleep=time.sleep) -> int:
    # 하루 호출 한도(2026-10-13 확인: K-apt 기본정보는 하루 약 1,300건에서 429)가 작아서,
    # 실거래 단지와 이미 연결된 단지 → 실거래가 있는 시군구 순으로 먼저 받는다 (세대수가 급지·회전율에 바로 쓰인다)
    todo = [r["kapt_code"] for r in select(db, "SELECT k.kapt_code FROM kapt_complexes k WHERE k.info_at IS NULL "
                                              "ORDER BY EXISTS (SELECT 1 FROM complexes c WHERE c.kapt_code = k.kapt_code) DESC, "
                                              f"k.region_code, k.kapt_code LIMIT {int(limit)}")]
    return _run_calls(db, todo, today, lambda c: fetch_info(c), info_row, INFO_COLS, "info_at", "기본 정보", sleep)


def run_detail(db: Db, limit: int, today: date, sleep=time.sleep) -> int:
    # 상세 정보는 실거래와 연결된 단지만 받는다 (H1 역세권·주차는 단지 화면용). 서울 → 경기·인천 순
    todo = [r["kapt_code"] for r in select(db, "SELECT k.kapt_code FROM kapt_complexes k WHERE k.detail_at IS NULL "
                                              "AND EXISTS (SELECT 1 FROM complexes c WHERE c.kapt_code = k.kapt_code) "
                                              f"ORDER BY k.region_code, k.kapt_code LIMIT {int(limit)}")]
    return _run_calls(db, todo, today, lambda c: fetch_detail(c), detail_row, DETAIL_COLS, "detail_at", "상세 정보", sleep)


def _run_calls(db: Db, todo: list[str], today: date, fetch, to_row, cols, at_col: str, label: str, sleep) -> int:
    done = fail = streak = pauses = 0
    batch: list[str] = []

    def flush() -> None:
        if batch:
            db.query("BEGIN;\n" + "\n".join(batch) + "\nCOMMIT;")
            batch.clear()

    def left() -> int:
        return select(db, f"SELECT count(*) AS n FROM kapt_complexes WHERE {at_col} IS NULL")[0]["n"]

    i = 0
    while i < len(todo):
        code = todo[i]
        try:
            item = fetch(code)
        except QuotaExceeded as e:
            flush()
            print(f"  {label} {done}개 받음, 중단(호출 한도 또는 연속 접속 실패): {e}", file=sys.stderr)
            return 2
        except ApiError as e:
            fail += 1
            streak += 1
            print(f"  {code}: 실패 {e}", file=sys.stderr)
            if streak >= FAIL_STREAK:
                flush()
                if pauses >= len(PAUSES):
                    print(f"  {label} {done}개 받음, 실패가 {streak}번 연달아 이어져 중단 (남은 단지 {left()}개)", file=sys.stderr)
                    return 2
                print(f"  실패 {streak}번 연속 → {PAUSES[pauses]}초 쉬고 {code}부터 다시", file=sys.stderr)
                sleep(PAUSES[pauses])
                pauses += 1
                streak = 0
                i -= FAIL_STREAK - 1          # 연속 실패한 단지들을 다시 부른다
            else:
                i += 1
            continue
        streak = 0
        pauses = 0
        row = to_row(item) if item else {}
        sets = ", ".join(f"{c} = {lit(row.get(c))}" for c in cols)
        batch.append(f"UPDATE kapt_complexes SET {sets}, {at_col} = {lit(today)} WHERE kapt_code = {lit(code)};")
        done += 1
        i += 1
        if len(batch) >= 200:
            flush()
            print(f"  {label} {done}/{len(todo)} 저장", flush=True)
    flush()
    print(f"  {label} {done}개 받음, 실패 {fail}, 남은 단지 {left()}개")
    return 1 if fail else 0


def run_match(db: Db, regions: list[str]) -> int:
    rl = ", ".join(lit(r) for r in regions)
    cx = select(db, "SELECT apt_seq, apt_name, bjd_code, jibun, road_addr FROM complexes "
                    f"WHERE region_code IN ({rl}) AND (match_method IS NULL OR match_method <> 'manual')")
    kp = select(db, f"SELECT kapt_code, kapt_name, bjd_code, addr, road_addr, sale_type FROM kapt_complexes WHERE region_code IN ({rl})")
    m = match_complexes(cx, kp)
    stmts = ["BEGIN;",
             f"UPDATE complexes SET kapt_code = NULL, match_method = NULL WHERE region_code IN ({rl}) AND match_method IS DISTINCT FROM 'manual';"]
    items = list(m.items())
    for i in range(0, len(items), 500):
        vals = ", ".join(f"({lit(s)}, {lit(x.kapt_code)}, {lit(x.method)})" for s, x in items[i:i + 500])
        stmts.append("UPDATE complexes AS c SET kapt_code = v.k, match_method = v.m "
                     f"FROM (VALUES {vals}) AS v(s, k, m) WHERE c.apt_seq = v.s;")
    stmts.append("COMMIT;")
    db.query("\n".join(stmts))
    by = {}
    for x in m.values():
        by[x.method] = by.get(x.method, 0) + 1
    print(f"  실거래 단지 {len(cx)}개 중 {len(m)}개 연결 {by} (K-apt 단지 {len(kp)}개)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["complexes", "list", "info", "detail", "match"])
    ap.add_argument("--regions", default="sudogwon")
    ap.add_argument("--months", default="202001-202608", help="complexes 모드용")
    ap.add_argument("--limit", type=int, default=5000, help="info·detail 모드: 한 번에 받을 단지 수")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    today = datetime.now(KST).date()
    db = connect(a.db)
    regions = select_regions(a.regions)
    t0 = time.monotonic()
    try:
        if a.mode == "complexes":
            rc = run_complexes(db, regions, parse_months(a.months), today)
        elif a.mode == "list":
            rc = run_list(db, regions, today)
        elif a.mode == "info":
            rc = run_info(db, a.limit, today)
        elif a.mode == "detail":
            rc = run_detail(db, a.limit, today)
        else:
            rc = run_match(db, regions)
    except DbError as e:
        print(f"DB 오류: {e}", file=sys.stderr)
        rc = 1
    print(f"[kapt] {a.mode} done in {time.monotonic() - t0:.0f}s rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
