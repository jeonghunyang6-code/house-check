-- 한강변 추정(collector/hanbank.py, jobs/infra.py hanbank, 2026-11-15 사용자 요청 A안). OSM 한강 물가 기준, 단지 중심 한 점이라 '추정'
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS han_bank_m INTEGER,   -- 한강 물가까지 직선(m), 2km 안만
  ADD COLUMN IF NOT EXISTS han_front  BOOLEAN,   -- 물가 400m 🔧 안이고 사이에 다른 아파트 단지 없음(1열 추정)
  ADD COLUMN IF NOT EXISTS han_block  TEXT;      -- 사이에 있는 단지 하나(확인용)
