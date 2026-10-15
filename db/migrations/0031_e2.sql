-- E2 주변 시세 위치 (sql/metrics.sql 5). 📖 주변 시세가 높은 곳이 상승 여력이 크다 p.216~217, p.339, p.342
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e2_ratio NUMERIC(5, 3);  -- 이 단지 ㎡당 기준 시세 ÷ 주변 단지(면적군 ±15㎡) ㎡당 기준 시세 중앙값. 1 미만 = 주변이 더 비쌈
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e2_n     INTEGER;        -- 비교한 주변 단지 수
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e2_basis TEXT;           -- 생활권 / 반경 1.5km
