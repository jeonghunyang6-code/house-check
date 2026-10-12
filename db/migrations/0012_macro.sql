-- 거시 월별 지표 (collector/sources/kosis.py, jobs/macro.py). 정의: docs/insights/indicators.md G1~G5.
-- 시계열마다 (series, period) 한 행. 발표 후 수정되면 덮어쓴다. ECOS 지표(금리·대출·M2)도 같은 표에 넣는다.
CREATE TABLE IF NOT EXISTS macro_monthly (
  series     TEXT    NOT NULL,   -- 예: unemployment_sa (계절조정 실업률)
  period     TEXT    NOT NULL CHECK (period ~ '^[0-9]{6}$'),  -- YYYYMM
  value      NUMERIC NOT NULL,
  fetched_at DATE    NOT NULL,
  PRIMARY KEY (series, period)
);

ALTER TABLE macro_monthly ENABLE ROW LEVEL SECURITY;
