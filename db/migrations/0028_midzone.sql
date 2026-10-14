-- 중학교 학교군 (한국교육시설안전원 15159264·15159266·15159184, jobs/infra.py midzone). 설명용, 점수화하지 않음(M3)
CREATE TABLE IF NOT EXISTS mid_school (
  school_id TEXT PRIMARY KEY,          -- 학구도 학교ID 'B000008373'
  name      TEXT NOT NULL,
  est_type  TEXT,                      -- 공립·사립·국립
  lat       DOUBLE PRECISION NOT NULL,
  lng       DOUBLE PRECISION NOT NULL,
  zone_ids  TEXT                       -- 이 학교가 든 학교군 HAKGUDO_ID (쉼표)
);
ALTER TABLE mid_school ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS mid_zone_id      TEXT,     -- 중학교 학교군·중학구 HAKGUDO_ID
  ADD COLUMN IF NOT EXISTS mid_zone         TEXT,     -- '강남서초 중학교군' 등
  ADD COLUMN IF NOT EXISTS mid_zone_shared  BOOLEAN,  -- 공동학구에도 걸침
  ADD COLUMN IF NOT EXISTS mid_zone_schools INTEGER,  -- 그 학교군(공동학구 포함) 중학교 수
  ADD COLUMN IF NOT EXISTS mid_school_id    TEXT,     -- 학교군 안 직선으로 가장 가까운 중학교 (실제 배정과 다를 수 있음)
  ADD COLUMN IF NOT EXISTS mid_school       TEXT,
  ADD COLUMN IF NOT EXISTS mid_school_m     INTEGER;
