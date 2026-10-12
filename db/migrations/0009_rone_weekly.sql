-- 한국부동산원 R-ONE 주간 아파트 가격동향 (collector/sources/rone.py, jobs/rone.py).
-- 매매·전세 지수는 서울·경기·인천 지역과 상위 집계(전국·수도권 등), 수급동향은 권역 단위 42개 지역 전체.
CREATE TABLE IF NOT EXISTS rone_regions (
  cls_id      INTEGER PRIMARY KEY,   -- R-ONE 지역 ID (서울 50008, 수도권 50002)
  full_name   TEXT NOT NULL,         -- '경기>경부2권>수원시>영통구'
  name        TEXT NOT NULL,
  region_code TEXT                   -- 우리 시군구 코드 (collector/regions.py), 시군구가 아니면 NULL
);

CREATE TABLE IF NOT EXISTS rone_weekly (
  stat      TEXT    NOT NULL CHECK (stat IN ('sale', 'jeonse', 'sale_supply', 'jeonse_supply')),
  cls_id    INTEGER NOT NULL,
  week_id   TEXT    NOT NULL CHECK (week_id ~ '^[0-9]{6}$'),  -- ISO 연도+주차 (202641 = 2026-10-05 주)
  week_date DATE    NOT NULL,
  value     DOUBLE PRECISION NOT NULL,  -- 지수(기준 2026.07.06=100) 또는 수급지수
  PRIMARY KEY (stat, cls_id, week_id)
);
CREATE INDEX IF NOT EXISTS rone_weekly_date_idx ON rone_weekly (stat, week_date);

ALTER TABLE rone_regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rone_weekly  ENABLE ROW LEVEL SECURITY;
