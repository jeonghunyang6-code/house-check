-- D2 매매·전세 4분면 재료: 지역 지수 13주(약 3개월) 변화. B6 상대강도: 단지 12개월 변화 − 같은 시군구 단지 중앙값.
ALTER TABLE region_phase    ADD COLUMN IF NOT EXISTS chg_13w        NUMERIC(6, 2);  -- 최신 주 ÷ 13주 전 − 1, %
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS region_chg_12m NUMERIC(6, 2);  -- 같은 시군구 국면 판정 단지들의 12개월 변화 중앙값
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS rel_strength   NUMERIC(6, 2);  -- chg_12m − region_chg_12m (%p)
