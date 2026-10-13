-- D3 역전세 위험, A6 실질 가격 (sql/metrics.sql). 정의: docs/insights/indicators.md
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS jeonse_24m_10k INTEGER;      -- 24개월 전(±1개월) 전세 계약 중앙값(건수 가중)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS jeonse_24m_n   INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS reverse_risk   BOOLEAN;      -- 현재 전세 < 24개월 전 전세 (📖 p.153)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS reserve_10k    INTEGER;      -- 역전세 대비금 = 현재 전세 × 10% (📖 p.153)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS real_ref_10k   INTEGER;      -- 기준 시세 ÷ CPI × 100 (2020=100 원화)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS base2020_10k   INTEGER;      -- 2020-01~03 중개 거래 중앙값
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS real_chg_2020  NUMERIC(6, 1); -- 2020년 1분기 대비 실질 변화 % (📖 물가만큼은 오른다 p.108~110)
