-- 수도권 초등학교 위치(jobs/infra.py elem, 공공데이터 초중등학교위치 15159184) + 단지의 통학구역 배정 초등학교(학교학구도연계정보 15159266).
-- 상세 탭 실제 지도에 🏫 로 표시. 통학구역은 complexes.school_zone_id(0025)
CREATE TABLE IF NOT EXISTS elem_school (
  school_id TEXT PRIMARY KEY,
  name      TEXT NOT NULL,
  est_type  TEXT,
  lat       NUMERIC(9, 6) NOT NULL,
  lng       NUMERIC(9, 6) NOT NULL
);
ALTER TABLE complexes ADD COLUMN IF NOT EXISTS elem_assigned JSONB;   -- [{"id","name","m"}] 통학구역 학교, 가까운 순 최대 3
