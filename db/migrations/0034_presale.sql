-- 입주 물량 F1 (jobs/presale.py, collector/presale.py, sql/metrics.sql 8). 📖 입주장 5~6개월 p.55, 입주 물량과 전세 p.154, p.423
CREATE TABLE IF NOT EXISTS presale (
  house_no    TEXT PRIMARY KEY,      -- 청약홈 주택관리번호
  name        TEXT NOT NULL,
  address     TEXT NOT NULL,
  area        TEXT,                  -- 서울·경기·인천
  households  INTEGER NOT NULL,      -- 공급 세대(일반+특별). 재건축·재개발 조합원 몫은 빠짐
  move_in_ym  TEXT NOT NULL,         -- 입주 예정 YYYYMM
  notice_date DATE,
  house_type  TEXT,
  lat DOUBLE PRECISION, lng DOUBLE PRECISION,
  geo_method  TEXT,                  -- jibun / dong / none
  region_code TEXT,                  -- 가장 가까운 단지(🔧 3km 안)의 시군구
  lifezone_id TEXT,                  -- 가장 가까운 단지의 생활권
  updated     DATE NOT NULL
);
ALTER TABLE presale ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS presale_move_in_idx ON presale (move_in_ym);
ALTER TABLE complex_metrics
  ADD COLUMN IF NOT EXISTS f1_zone_24m INTEGER,   -- 같은 생활권 앞으로 24개월 입주 공급 세대
  ADD COLUMN IF NOT EXISTS f1_sgg_24m  INTEGER,   -- 같은 시군구 앞으로 24개월
  ADD COLUMN IF NOT EXISTS f1_ipju     TEXT,      -- 입주장: 같은 생활권에서 입주 시작 6개월 안인 단지 '이름(YYYY.MM, 세대)'
  ADD COLUMN IF NOT EXISTS f1_next     TEXT;      -- 같은 생활권 앞으로 24개월 중 가장 큰 입주
