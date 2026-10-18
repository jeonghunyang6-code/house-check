-- C3 하락기 환금성·C4 거래 유지율 (collector/liquidity.py, jobs/liquidity.py). 단지 단위, 한 번 계산(다음 하락기에 다시).
-- 📖 하락장에 거래가 많았던 단지 = 환금성 좋음 p.138~142. 회전율 = 월평균 중개 거래 ÷ 세대수 × 100 (%)
CREATE TABLE IF NOT EXISTS complex_liquidity (
  apt_seq        TEXT PRIMARY KEY,
  region_code    TEXT NOT NULL,
  households     INTEGER NOT NULL,
  peak_m         TEXT NOT NULL,       -- 지역 매매지수 고점 달 (상승 구간 끝)
  trough_m       TEXT NOT NULL,       -- 저점 달 (하락 구간 끝)
  drop_pct       NUMERIC(6, 2),       -- 지역 지수 고점 → 저점 (%)
  window_src     TEXT NOT NULL CHECK (window_src IN ('sgg', 'sido')),
  down_n         INTEGER NOT NULL,    -- 하락 구간 중개 거래 수
  down_turnover  NUMERIC(8, 3) NOT NULL,   -- C3 하락 구간 월 회전율 (%)
  down_rank      NUMERIC(5, 1),       -- C3 같은 시군구 안 분위 (0 = 가장 적음, 100 = 가장 많음)
  up_n           INTEGER,             -- 상승 구간(2020-01 ~ 고점) 중개 거래 수
  up_turnover    NUMERIC(8, 3),
  keep_ratio     NUMERIC(8, 3),       -- C4 = 하락 ÷ 상승 회전율
  keep_rank      NUMERIC(5, 1),
  asof           DATE NOT NULL
);
ALTER TABLE complex_liquidity ENABLE ROW LEVEL SECURITY;
