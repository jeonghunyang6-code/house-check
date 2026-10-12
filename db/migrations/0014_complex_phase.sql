-- 단지 × 면적군 B1 국면 (sql/metrics.sql). 지역 국면(region_phase)과 같은 규칙을 실거래 월별 기준 시세에 적용한다.
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS phase       TEXT;           -- 상승장 | 하락장 | 보합장 | 일시 반등 | 일시 조정 | 추세 불명확 | NULL(거래 부족)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS chg_12m     NUMERIC(6, 2);  -- 12개월 누적 변화 %
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS up_months   INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS down_months INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS last3       TEXT;
