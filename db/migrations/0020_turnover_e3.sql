-- C2 월 거래 회전율, E3 바로 위 급지 비교 단지·B6 상대강도(위 급지 대비) (sql/metrics.sql 끝의 UPDATE). 정의: docs/insights/indicators.md
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS households      INTEGER;        -- K-apt 세대수
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS turnover_pct    NUMERIC(5, 2);  -- 단지 월 거래(해제 제외) ÷ 세대수 × 100, 집계 끝난 최근 12개월 평균 (📖 0.5~0.8% p.137)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS turnover_state  TEXT;           -- 적음 / 꽤 괜찮음 / 많음
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e3_seqs         TEXT;           -- 비교 단지 apt_seq (쉼표, 최대 3)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e3_target_10k   INTEGER;        -- 목표 시세 = 비교 단지 ㎡당 기준 시세 중앙값 × 이 면적군 (📖 p.358~359)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e3_chg_12m      NUMERIC(6, 2);  -- 비교 단지 12개월 변화 중앙값 (B1 판정 단지만)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS rel_strength_e3 NUMERIC(6, 2);  -- chg_12m − e3_chg_12m (📖 상승의 차이 p.420~421)
