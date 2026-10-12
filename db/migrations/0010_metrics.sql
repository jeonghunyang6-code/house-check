-- 단지 지표 (jobs/metrics.py, sql/metrics.sql). 매일 매매 수집 뒤 다시 계산해 덮어쓴다. 화면은 읽기만 한다.
-- 정의: docs/insights/indicators.md A1(기준 시세)·B2(전고점 회복 패턴)·C2 준비(1년 거래 수)·D1(전세가율 정상 범위),
--       docs/ARCHITECTURE.md 4.3(신고가: 이전 계약일의 중개·비해제 최고가).

-- 거래별 전고점. 최근 계약분은 매일 다시 계산한다(늦게 신고된 이전 거래가 들어올 수 있음).
ALTER TABLE deals ADD COLUMN IF NOT EXISTS prev_high_10k INTEGER;

CREATE TABLE IF NOT EXISTS complex_metrics (
  apt_seq         TEXT    NOT NULL,
  area_group      INTEGER NOT NULL,
  asof            DATE    NOT NULL,
  -- A1 기준 시세: 최근 60일 중개·비해제 중앙값, 3건 미만이면 90일 → 180일
  ref_10k         INTEGER,
  ref_n           INTEGER,
  ref_days        INTEGER,          -- 60 | 90 | 180
  confidence      TEXT CHECK (confidence IN ('높음', '보통', '낮음')),
  -- B2 전고점 회복: P = 2021-01~2022-06 최고 월별 기준 시세(3개월 이동 중앙값), T = 2022-07~2023-06 최저
  peak_10k        INTEGER,
  peak_month      TEXT,
  trough_10k      INTEGER,
  trough_month    TEXT,
  recovery        NUMERIC(6, 3),    -- (C - T) / (P - T)
  pattern         TEXT CHECK (pattern IN ('신고가 돌파', '순조로운 회복', '회복 지연')),
  no_rebound      BOOLEAN,          -- C <= T × 1.03 (2023년 초 대비 반등 없음 경고)
  -- D1 전세가율: 당월·전월 신규 전세 중앙값(없으면 전체 전세) ÷ 기준 시세
  jeonse_10k      INTEGER,
  jeonse_n        INTEGER,
  jeonse_src      TEXT CHECK (jeonse_src IN ('신규', '전체')),
  jeonse_ratio    NUMERIC(5, 1),    -- %
  band_lo         NUMERIC(4, 1),    -- 가격대별 정상 범위 (책 p.152, 사이 가격대는 선형 보간)
  band_hi         NUMERIC(4, 1),
  -- 거래
  n_365           INTEGER,          -- 최근 1년 중개·비해제 거래 수 (회전율 C2 는 K-apt 세대수 연결 후)
  high_10k        INTEGER,          -- 수집된 기간 최고가 (중개·비해제)
  high_date       DATE,
  last_date       DATE,
  PRIMARY KEY (apt_seq, area_group)
);
CREATE INDEX IF NOT EXISTS complex_metrics_pattern_idx ON complex_metrics (pattern);
ALTER TABLE complex_metrics ENABLE ROW LEVEL SECURITY;
