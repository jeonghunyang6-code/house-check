-- B2 회복 패턴 계속 검증 (jobs/b2_check.py, rone.yml 매주 — 스냅숏은 분기마다 한 번).
-- 2026-10-19 백테스트에서 2024년 판정이 이후 2년 상대 상승률을 가르지 못해 비교표 점수에서 뺐다(docs/insights/backtests.md).
-- 분기마다 그때의 판정을 저장하고, 12·24개월 뒤 같은 단지 기준 시세와 비교해(같은 시군구 중앙값 대비) 패턴별 결과를 쌓는다
CREATE TABLE IF NOT EXISTS b2_snapshot (
  asof        DATE    NOT NULL,
  apt_seq     TEXT    NOT NULL,
  area_group  INTEGER NOT NULL,
  region_code TEXT    NOT NULL,
  pattern     TEXT    NOT NULL,
  recovery    NUMERIC(6, 3),
  ref_10k     INTEGER NOT NULL,
  PRIMARY KEY (asof, apt_seq, area_group)
);
CREATE TABLE IF NOT EXISTS b2_validation (
  asof         DATE    NOT NULL,     -- 판정 시점
  horizon_m    INTEGER NOT NULL,     -- 몇 개월 뒤와 비교했나
  pattern      TEXT    NOT NULL,
  n            INTEGER NOT NULL,
  mean_excess  NUMERIC(7, 2),        -- 같은 시군구 중앙값 대비 초과 상승 평균 (%p)
  beat_pct     NUMERIC(5, 1),        -- 시군구 중앙값보다 더 오른 비율 (%)
  source       TEXT    NOT NULL,     -- 'snapshot'(자동) | 'backtest'(2026-10-19 보관 파일 백테스트, 84㎡)
  evaluated_at DATE    NOT NULL,
  PRIMARY KEY (asof, horizon_m, pattern, source)
);
ALTER TABLE b2_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE b2_validation ENABLE ROW LEVEL SECURITY;
