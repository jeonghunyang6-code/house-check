-- C6 거래 적은 이유 (관점 V3, ▶ "도대체 얼마야?" 3:51, 📖 p.472~473): 수요 부족 vs 공급(세대수) 부족. sql/metrics.sql 11.
-- 이 면적군이 속한 K-apt 전용면적 구간(60 이하·60~85·85~135·135 초과)의 세대수와 그 구간 월 회전율(C2 와 같은 12개월)
ALTER TABLE complex_metrics
  ADD COLUMN IF NOT EXISTS c6_band_hh   INTEGER,        -- 같은 전용면적 구간 세대수
  ADD COLUMN IF NOT EXISTS c6_band_turn NUMERIC(6, 2),  -- 그 구간 월 거래 ÷ 구간 세대수 (%)
  ADD COLUMN IF NOT EXISTS c6_region_med NUMERIC(6, 2), -- 같은 시군구·같은 구간 단지들의 구간 회전율 중앙값
  ADD COLUMN IF NOT EXISTS c6_reason    TEXT;           -- 구간 회전율이 구 중앙값의 절반 미만일 때: '세대수 적음' | '이 평형만 적음' | '단지 전체 적음'
