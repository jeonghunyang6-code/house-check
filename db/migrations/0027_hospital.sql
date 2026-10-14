-- 병원 (심평원 병원정보서비스 getHospBasisList, collector/hira.py). 설명용, 점수화하지 않음
CREATE TABLE IF NOT EXISTS hospital (
  hospital_id SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  kind        TEXT,                    -- '상급종합', '종합병원'
  lat         DOUBLE PRECISION NOT NULL,
  lng         DOUBLE PRECISION NOT NULL
);
ALTER TABLE hospital ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS hosp_name  TEXT,      -- 가장 가까운 상급종합·종합병원 (직선, 5km 안)
  ADD COLUMN IF NOT EXISTS hosp_kind  TEXT,
  ADD COLUMN IF NOT EXISTS hosp_m     INTEGER,
  ADD COLUMN IF NOT EXISTS clinic_1km INTEGER;   -- 직선 1km 안 의원 수
