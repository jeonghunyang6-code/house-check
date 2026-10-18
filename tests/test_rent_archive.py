import os
import tempfile
from datetime import date
from pathlib import Path

from collector.archive import LocalDirStore, asset_name, decode, encode, merge
from collector.db import PsqlDb, select
from collector.pg_store import RENT, apply_snapshot_pg
from collector.rent_stats import rent_to_row, summarize
from collector.snapshot import keyed
from collector.sources.molit import parse_rent_page
from jobs.rent_archive import backfill, daily

ROOT = Path(__file__).parent.parent
RENT_XML = (Path(__file__).parent / "fixtures" / "molit_rent_sample.xml").read_text(encoding="utf-8")
URL = os.environ.get("HC_TEST_PG_URL")


def _rents():
    return parse_rent_page(RENT_XML)[0]


def _rows(region="11680", month="202609"):
    return [rent_to_row(k, region, month, x) for k, x in keyed(_rents()).items()]


def test_encode_decode_roundtrip_and_deterministic():
    rows = _rows()
    data = encode(rows)
    assert data == encode(rows)  # mtime=0
    back = decode(data)
    assert len(back) == len(rows) and back[0]["rent_key"] == rows[0]["rent_key"]
    assert {r["used_renewal_right"] for r in back} <= {"0", "1"}


def test_merge_replaces_only_given_regions():
    a, b = _rows("11680"), _rows("11710")
    for r in b:
        r["rent_key"] = r["rent_key"].replace("11680-", "11710-")
    both = merge([], a + b, {"11680", "11710"})
    again = merge(both, a[:2], {"11680"})
    assert sum(r["region_code"] == "11680" for r in again) == 2
    assert sum(r["region_code"] == "11710" for r in again) == len(b)


def test_summarize_counts():
    s = summarize(_rows())
    assert sum(x["n_jeonse"] + x["n_wolse"] for x in s) == 5
    assert sum(x["n_type_blank"] for x in s) == 1
    assert sum(x["n_renewal_right_used"] for x in s) >= 1
    for x in s:
        assert (x["jeonse_median_10k"] is None) == (x["n_jeonse"] == 0)
    gone = _rows()
    gone[0]["disappeared"] = True
    assert sum(x["n_jeonse"] + x["n_wolse"] for x in summarize(gone)) == 4


def _db():
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, rent_events, rents, snapshot_runs, rent_monthly, "
             "archive_cells CASCADE;")
    for m in ("0001_deals.sql", "0005_snapshot_runs.sql", "0006_rents.sql", "0007_rent_archive.sql",
              "0038_archive_recheck.sql"):
        db.query((ROOT / "db" / "migrations" / m).read_text(encoding="utf-8"))
    return db


def test_backfill_writes_file_and_summary_then_skips():
    if not URL:
        return
    db, store = _db(), LocalDirStore(tempfile.mkdtemp())
    calls = []

    def fake_fetch(code, month):
        calls.append((code, month))
        return _rents()

    assert backfill(db, store, ["11680"], ["202301", "202302"], date(2026, 10, 12), fetch=fake_fetch) == 0
    assert len(decode(store.get(asset_name("rent", "202301")))) == 5
    cells = select(db, "SELECT contract_month, n_rows, source FROM archive_cells ORDER BY 1")
    assert [(c["contract_month"], c["n_rows"], c["source"]) for c in cells] == \
           [("202301", 5, "api_backfill"), ("202302", 5, "api_backfill")]
    assert select(db, "SELECT sum(n_jeonse + n_wolse) AS n FROM rent_monthly WHERE contract_month = '202301'")[0]["n"] == 5
    assert select(db, "SELECT count(*) AS n FROM rents")[0]["n"] == 0  # 과거 이력은 DB 원본에 넣지 않는다
    calls.clear()
    assert backfill(db, store, ["11680"], ["202301", "202302"], date(2026, 10, 12), fetch=fake_fetch) == 0
    assert calls == []  # 이미 보관한 칸은 건너뛴다


def test_daily_rolls_old_month_to_file_and_deletes():
    if not URL:
        return
    db, store = _db(), LocalDirStore(tempfile.mkdtemp())
    rents = _rents()
    apply_snapshot_pg(db, "11680", "202609", rents[:3], date(2026, 10, 11), True, kind=RENT)
    apply_snapshot_pg(db, "11680", "202609", rents, date(2026, 10, 12), False, kind=RENT)  # 2건 신규 등록
    # 10월 중: 202609 는 일일 범위 → 요약만 갱신, DB 원본 유지
    assert daily(db, store, date(2026, 10, 12)) == 0
    assert select(db, "SELECT count(*) AS n FROM rents")[0]["n"] == 5
    assert select(db, "SELECT sum(n_jeonse + n_wolse) AS n FROM rent_monthly")[0]["n"] == 5
    assert store.get(asset_name("rent", "202609")) is None
    # 11월: 202609 가 범위를 벗어남 → 파일로 옮기고 DB 에서 삭제. 등록일(first_seen)도 파일에 남는다
    assert daily(db, store, date(2026, 11, 3)) == 0
    assert select(db, "SELECT count(*) AS n FROM rents")[0]["n"] == 0
    assert select(db, "SELECT count(*) AS n FROM rent_events")[0]["n"] == 0
    f = decode(store.get(asset_name("rent", "202609")))
    assert len(f) == 5 and sum(r["first_seen_date"] == "2026-10-12" for r in f) == 2
    assert select(db, "SELECT source FROM archive_cells")[0]["source"] == "db_rollover"
    assert select(db, "SELECT sum(n_jeonse + n_wolse) AS n FROM rent_monthly")[0]["n"] == 5
    assert daily(db, store, date(2026, 11, 4)) == 0  # 다시 돌려도 문제없다


def test_recheck_rows_keeps_first_seen_adds_late_and_marks_gone():
    from jobs.rent_archive import recheck_rows
    rents = _rents()
    old = [rent_to_row(k, "11680", "202601", x, "2026-01-20", "2026-02-28") for k, x in keyed(rents[:4]).items()]
    got = rents[1:]  # 첫 건은 빠지고 마지막 건은 늦게 들어옴
    rows, added, gone = recheck_rows(old, got, "11680", "202601", date(2026, 10, 18))
    assert (added, gone) == (1, 1) and len(rows) == 6 - 1
    by = {r["rent_key"]: r for r in rows}
    assert sum(r["disappeared"] is True for r in rows) == 1
    assert sum(r["first_seen_date"] == "2026-10-18" for r in rows) == 1
    assert sum(r["first_seen_date"] == "2026-01-20" for r in by.values()) == 4
    again, a2, g2 = recheck_rows(rows, got, "11680", "202601", date(2026, 10, 28))
    assert (a2, g2) == (0, 0) and len(again) == len(rows)


def test_recheck_updates_file_and_summary():
    if not URL:
        return
    from jobs.daily import recheck_month
    from jobs.rent_archive import recheck
    db, store = _db(), LocalDirStore(tempfile.mkdtemp())
    today = date(2026, 10, 18)
    m = recheck_month(today)
    rents = _rents()
    assert backfill(db, store, ["11680"], [m], today, fetch=lambda c, mm: rents[:3]) == 0
    assert recheck(db, store, today, fetch=lambda c, mm: rents) == 0
    f = decode(store.get(asset_name("rent", m)))
    assert len(f) == 5 and sum(r["first_seen_date"] == "2026-10-18" for r in f) == 2
    assert select(db, "SELECT sum(n_jeonse + n_wolse) AS n FROM rent_monthly")[0]["n"] == 5
    assert select(db, "SELECT source FROM archive_cells")[0]["source"] == "recheck"
    assert recheck(db, store, today, fetch=lambda c, mm: []) == 0  # 빈 응답은 기존 유지
    assert len(decode(store.get(asset_name("rent", m)))) == 5
