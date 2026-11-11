-- 공원 (전국도시공원정보표준데이터, collector/parks.py, jobs/infra.py park). 입지 사실표 설명용, 점수화하지 않음(2026-11-11 사용자 요청)
CREATE TABLE IF NOT EXISTS park (
  park_id SERIAL PRIMARY KEY,
  name    TEXT NOT NULL,
  kind    TEXT,                    -- 공원구분(근린공원·체육공원 …). 어린이공원·소공원은 넣지 않음
  area_m2 DOUBLE PRECISION,
  lat     DOUBLE PRECISION NOT NULL,
  lng     DOUBLE PRECISION NOT NULL
);
ALTER TABLE park ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS park_name TEXT,     -- 가장 가까운 근린공원 이상 (직선, 2km 안)
  ADD COLUMN IF NOT EXISTS park_kind TEXT,
  ADD COLUMN IF NOT EXISTS park_area DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS park_m    INTEGER;
