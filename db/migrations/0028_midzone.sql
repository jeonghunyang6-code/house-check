-- 중학교 학교군 (한국교육시설안전원 15159264·15159266·15159184, 학교알리미 전·출입; jobs/infra.py midzone). 설명용, 점수화하지 않음(M3)
-- 학교군 안 거리·추첨 배정이라 학교가 여럿이면 배정 학교를 확정할 수 없다 → '배정 가능 학교들'로 보여준다
CREATE TABLE IF NOT EXISTS mid_school (
  school_id TEXT PRIMARY KEY,          -- 학구도 학교ID 'B000008373'
  name      TEXT NOT NULL,
  est_type  TEXT,                      -- 공립·사립·국립
  lat       DOUBLE PRECISION NOT NULL,
  lng       DOUBLE PRECISION NOT NULL,
  zone_ids  TEXT,                      -- 이 학교가 든 학교군 HAKGUDO_ID (쉼표)
  si_code   TEXT,                      -- 학교알리미 SCHUL_CODE 'S010000698'
  students  INTEGER,                   -- 학교알리미 전·출입 공시의 학생 수
  mv_in     INTEGER,                   -- 전입
  mv_out    INTEGER,                   -- 전출
  net_in    NUMERIC,                   -- (전입 − 전출) ÷ 학생 수 × 100
  pban_yr   TEXT                       -- 공시 연도
);
ALTER TABLE mid_school ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS mid_zone_id      TEXT,     -- 중학교 학교군·중학구 HAKGUDO_ID
  ADD COLUMN IF NOT EXISTS mid_zone         TEXT,     -- '강남서초2학교군' 등
  ADD COLUMN IF NOT EXISTS mid_zone_shared  BOOLEAN,  -- 공동학구에도 걸침
  ADD COLUMN IF NOT EXISTS mid_zone_schools INTEGER,  -- 그 학교군(공동학구 포함) 중학교 수
  ADD COLUMN IF NOT EXISTS mid_assigned     BOOLEAN,  -- 학교가 1곳뿐 → 배정 확정
  ADD COLUMN IF NOT EXISTS mid_near         JSONB,    -- 가까운 순 최대 3곳 [{id, name, m, net_in}] (배정 확정 아님)
  ADD COLUMN IF NOT EXISTS mid_zone_net_in  NUMERIC;  -- 학교군 전체 순전입률 (학생 수 가중)
