-- F3 미분양 + 원인 (📖 원인 5가지 p.155~160: 분양가 과다·입지·상품성·공급 집중·거시).
-- 1) 시군구별 미분양·준공 후 미분양 (KOSIS 국토부 DT_MLTM_2082·5328, jobs/macro.py). 경기는 시 단위라 region_codes 가 여러 개
CREATE TABLE IF NOT EXISTS unsold_sgg (
  period       TEXT NOT NULL CHECK (period ~ '^[0-9]{6}$'),
  sido         TEXT NOT NULL,
  name         TEXT NOT NULL,          -- KOSIS 표기 (경기 '수원시', 인천 '영종구')
  region_codes TEXT,                   -- 우리 시군구 코드, 쉼표로 (못 맞추면 NULL)
  unsold       INTEGER NOT NULL,       -- 미분양 (호)
  unsold_done  INTEGER,                -- 그중 준공 후 미분양
  PRIMARY KEY (period, sido, name)
);
ALTER TABLE unsold_sgg ENABLE ROW LEVEL SECURITY;
-- 2) 분양가 (청약홈 주택형별 getAPTLttotPblancMdl, jobs/presale.py prices) 와 주변 시세 비교
ALTER TABLE presale
  ADD COLUMN IF NOT EXISTS price_ppm_10k  NUMERIC(8, 1),   -- 전용 ㎡당 분양가(주택형별 최고가, 공급 세대 가중 중앙값, 만원)
  ADD COLUMN IF NOT EXISTS price84_10k    INTEGER,         -- 전용 80~89㎡ 주택형 최고 분양가
  ADD COLUMN IF NOT EXISTS price_types    INTEGER,         -- 주택형 수 (0 = 받았지만 가격 없음)
  ADD COLUMN IF NOT EXISTS price_ratio    NUMERIC(5, 2),   -- ㎡당 분양가 ÷ 같은 생활권(없으면 1.5km) 기준 시세 중앙값
  ADD COLUMN IF NOT EXISTS price_ratio_new NUMERIC(5, 2),  -- ÷ 같은 생활권 신축(준공 5년 이내, E7) ㎡당 시세
  ADD COLUMN IF NOT EXISTS price_ref_n    INTEGER;         -- 비교한 단지 수
