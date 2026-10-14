-- 생활 인프라 (jobs/infra.py, collector/infra.py). 입지는 점수화하지 않고 설명에만 쓴다(M3)
CREATE TABLE IF NOT EXISTS station (
  station_id SERIAL PRIMARY KEY,
  name       TEXT NOT NULL,           -- '강남' ('역'·괄호 뺀 이름)
  lines      TEXT,                    -- '2호선, 신분당선'
  lat        DOUBLE PRECISION NOT NULL,
  lng        DOUBLE PRECISION NOT NULL,
  sources    TEXT                     -- 공공데이터포털 데이터 번호
);
ALTER TABLE station ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS station_name   TEXT,     -- 가장 가까운 역 (직선)
  ADD COLUMN IF NOT EXISTS station_lines  TEXT,
  ADD COLUMN IF NOT EXISTS station_m      INTEGER,  -- 직선거리 m (📖 역세권 700m p.220)
  ADD COLUMN IF NOT EXISTS school_zone_id TEXT,     -- 초등학교 통학구역 HAKGUDO_ID (한국교육시설안전원, 15159265)
  ADD COLUMN IF NOT EXISTS school_zone    TEXT,     -- '잠실초통학구역'
  ADD COLUMN IF NOT EXISTS school_zone_shared BOOLEAN;  -- 공동통학구역(HAKGUDO_GB=1)에도 걸침
