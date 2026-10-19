-- D4 전세 하락 원인(📖 주변 신규 입주·매매가 하락 p.153~154, p.423), A5 거래 없는 평형 추정(📖 대체 평형 p.472~473, ▶ P3) — sql/metrics.sql 9·10
ALTER TABLE complex_metrics
  ADD COLUMN IF NOT EXISTS d4_jeonse_chg NUMERIC(6, 2),   -- 전세 1년 변화 % (지지난 달까지 3개월 vs 1년 전 같은 3개월, rent_monthly 근사)
  ADD COLUMN IF NOT EXISTS d4_n          TEXT,            -- '지금 n / 1년 전 n' 건수
  ADD COLUMN IF NOT EXISTS d4_cause      TEXT,            -- 전세가 🔧 3% 넘게 내렸을 때만: 입주 물량 / 매매 하락 / 입주 물량+매매 하락 / 둘 다 아님
  ADD COLUMN IF NOT EXISTS a5_est_10k    INTEGER,         -- 기준 시세가 없는 면적군의 추정가
  ADD COLUMN IF NOT EXISTS a5_from_ag    INTEGER,         -- 추정에 쓴 같은 단지 면적군
  ADD COLUMN IF NOT EXISTS a5_n          INTEGER;         -- 비율 계산에 쓴 거래 수(두 면적군 중 작은 쪽)
