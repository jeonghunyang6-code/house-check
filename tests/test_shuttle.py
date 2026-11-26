"""회사 셔틀(2026-11-26): 노선표 → shuttle_stops, 그리고 내부 자료가 공개 쪽으로 새지 않는지 지키는 테스트.
노선표 예시는 지어낸 값(실제 정류장·시각 아님)."""
import os
import subprocess
import tempfile
from pathlib import Path

from jobs.shuttle_load import load_sql, parse

ROOT = Path(__file__).parent.parent
URL = os.environ.get("HC_TEST_PG_URL")
HEAD = "캠퍼스,노선형태,지역,노선명,회차,근무구분,운행,순번,정류장명,시각,승하차,위도,경도,카카오맵\n"
FAKE = HEAD + "\n".join([
    "가,출근,서울(가),가선 (통상출근),통상 출근,통상,평일,1,가정류장,07:00,승차,37.5,127.1,x",
    "가,출근,서울(가),가선 (통상출근),통상 출근,통상,평일,2,회사[가캠퍼스],08:00,하차,37.2,127.4,x",
    "가,출근,서울(가),나선,통상 출근,통상,평일,1,가정류장,06:50,승차,37.5,127.1,x",
    "가,출근,서울(가),나선,통상 출근,통상,평일,2,회사[가캠퍼스],07:55,하차,37.2,127.4,x",
    "가,출근,서울(가),다선,A조 출근,교대,매일,1,나정류장,05:10,승차,37.6,127.2,x",          # 교대 → 빠짐
    "가,퇴근,서울(가),가선,통상 18시퇴근,통상,평일,1,회사[가캠퍼스],18:00,승차,37.2,127.4,x",
    "가,퇴근,서울(가),가선,통상 18시퇴근,통상,평일,2,가정류장,18:02,하차,37.5,127.1,x",
    "가,퇴근,서울(가),가선,통상 21시퇴근 ,통상,평일,1,회사[가캠퍼스],21:00,승차,37.2,127.4,x",
    "가,퇴근,서울(가),가선,통상 21시퇴근 ,통상,평일,2,가정류장,21:02,하차,37.5,127.1,x",
]) + "\n"


def _csv():
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8-sig")
    f.write(FAKE)
    f.close()
    return f.name


def test_parse_keeps_only_regular_shift_and_merges_hours():
    o, h = parse(_csv())
    assert sorted((x[0], x[3], x[4], x[5]) for x in o) == [("가정류장", "가선", "07:00", "08:00"), ("가정류장", "나선", "06:50", "07:55")]
    assert h == [("가정류장", 37.5, 127.1, "가선", "18,21")]          # 출발 시 합집합, 하차 시각(순서용)은 안 씀
    assert "나정류장" not in load_sql(o, h)                            # 교대 노선 빠짐


def test_migration_locks_table():
    sql = (ROOT / "db/migrations/0089_shuttle.sql").read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in sql and "REVOKE ALL ON shuttle_stops FROM anon, authenticated" in sql


def test_shuttle_never_goes_public():
    """공개 데이터(data.json)를 만드는 코드가 셔틀 표를 읽지 않고, 노선표 CSV·덤프가 저장소에 없다."""
    for p in ("tools/prototype/extract.py", "tools/prototype/compute.py", "tools/prototype/build_v2.py", "tools/prototype/template_v2.html"):
        assert "shuttle_stops" not in (ROOT / p).read_text(encoding="utf-8"), p
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    for f in files:
        if f.endswith((".csv", ".json", ".txt")) and (ROOT / f).is_file() and (ROOT / f).stat().st_size < 50_000_000:
            head = (ROOT / f).read_text(encoding="utf-8", errors="ignore")[:4000]
            assert "노선형태" not in head and "승하차" not in head, f
    api = (ROOT / "web/api/shuttle.js").read_text(encoding="utf-8")
    assert "timingSafeEqual" in api and "no-store" in api and "x-hc-key" in api


def test_load_sql_roundtrip():
    if not URL:
        return
    from collector.db import PsqlDb, select
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS shuttle_stops;")
    db.query("DO $$ BEGIN CREATE ROLE anon; EXCEPTION WHEN duplicate_object THEN NULL; END $$; DO $$ BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    db.query((ROOT / "db/migrations/0089_shuttle.sql").read_text(encoding="utf-8"))
    o, h = parse(_csv())
    db.query(load_sql(o, h))
    db.query(load_sql(o, h))                                              # 다시 넣어도 통째로 바뀜
    assert select(db, "SELECT kind, count(*) AS n FROM shuttle_stops GROUP BY 1 ORDER BY 1") == [{"kind": "h", "n": 1}, {"kind": "o", "n": 2}]
