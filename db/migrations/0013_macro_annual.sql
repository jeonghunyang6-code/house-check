-- macro_monthly 에 연간 지표(가계 처분가능소득 등)도 넣는다: period 가 YYYY 이면 연간, YYYYMM 이면 월간.
ALTER TABLE macro_monthly DROP CONSTRAINT IF EXISTS macro_monthly_period_check;
ALTER TABLE macro_monthly ADD CONSTRAINT macro_monthly_period_check CHECK (period ~ '^[0-9]{4}([0-9]{2})?$');
