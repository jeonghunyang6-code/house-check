-- H5 재건축 사업성 재료: 건축물대장 총괄표제부(없으면 공동주택 표제부 합) (collector/bldg.py, jobs/bldg.py, bldg.yml 매일 한도만큼)
-- 대상 🔧 2005년 이전 준공 단지(2027~28년에 20년+). 오래된 단지는 대지면적·용적률이 비어 있는 경우가 많다
CREATE TABLE IF NOT EXISTS complex_bldg (
  apt_seq      TEXT PRIMARY KEY,
  src          TEXT NOT NULL CHECK (src IN ('recap', 'title', 'none')),   -- none = 대장 못 찾음(산 지번·주소 다름)
  plat_area    NUMERIC(12, 2),   -- 대지면적 ㎡
  vl_rat       NUMERIC(7, 2),    -- 대장에 적힌 용적률 %
  vl_rat_calc  NUMERIC(7, 1),    -- 용적률 산정용 연면적 ÷ 대지면적 × 100
  estm_area    NUMERIC(12, 2),   -- 용적률 산정용 연면적 ㎡
  tot_area     NUMERIC(12, 2),   -- 연면적 ㎡
  hhld         INTEGER,          -- 세대수(대장)
  main_bld     INTEGER,          -- 주건축물 수
  land_per_hh  NUMERIC(8, 1),    -- 세대당 대지면적(대지지분 근사) ㎡
  fetched_at   DATE NOT NULL
);
ALTER TABLE complex_bldg ENABLE ROW LEVEL SECURITY;
