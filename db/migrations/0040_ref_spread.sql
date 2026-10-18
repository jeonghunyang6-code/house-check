-- A1 자료 충분도 근거: 기준 시세 창(ref_days) 안 거래의 가격 범위와 뺀 1층 건수 (sql/metrics.sql 2-1)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS ref_lo_10k   INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS ref_hi_10k   INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS ref_floor1_n INTEGER;
