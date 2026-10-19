-- E8 상급지까지 거리 (관점 D1 절대거리, 📖 p.85~103, collector/locality.py, jobs/locality.py). 급지 E1 최신 asof 기준, 매주 다시 쓴다
CREATE TABLE IF NOT EXISTS complex_e8 (
  apt_seq   TEXT PRIMARY KEY,
  grade     SMALLINT,          -- 이 단지 동의 급지 (없으면 NULL)
  up_rc     TEXT,              -- 가장 가까운 위 급지 동
  up_dong   TEXT,
  up_grade  SMALLINT,
  up_m      INTEGER,           -- 동 중심까지 직선거리 (m)
  top_rc    TEXT,              -- 가장 가까운 🔧 1~2급지 동 (이 단지가 1~2급지면 NULL)
  top_dong  TEXT,
  top_m     INTEGER,
  grade_asof DATE NOT NULL
);
ALTER TABLE complex_e8 ENABLE ROW LEVEL SECURITY;
