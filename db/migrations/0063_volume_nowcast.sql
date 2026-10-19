-- C1 신고 지연 보정 거래량 (collector/volume.py, jobs/volume.py, daily.yml 매일).
-- 날마다 그날의 추정을 남기고, 계약 달이 끝나고 90일이 지나면 그때 보이는 건수(actual)를 채워 추정이 맞았는지 본다
CREATE TABLE IF NOT EXISTS volume_nowcast (
  asof           DATE    NOT NULL,
  region_code    TEXT    NOT NULL,    -- '11' 서울 · '28' 인천 · '41' 경기 · 'capital' 수도권
  contract_month TEXT    NOT NULL,
  observed       INTEGER NOT NULL,    -- 그날까지 보인 거래(해제 제외)
  share          NUMERIC(5, 3) NOT NULL,   -- 지금까지 계약된 것 중 보이는 비율(추정)
  month_frac     NUMERIC(5, 3) NOT NULL,   -- 한 달 중 지난 비율(요일 가중)
  est            INTEGER NOT NULL,    -- 지금까지 계약된 거래 추정
  lo             INTEGER,
  hi             INTEGER,
  est_full       INTEGER,             -- 그 달 전체 추정
  n_lags         INTEGER NOT NULL,    -- 지연 표본 수
  actual         INTEGER,             -- 90일 뒤 보인 건수(검증)
  PRIMARY KEY (asof, region_code, contract_month)
);
ALTER TABLE volume_nowcast ENABLE ROW LEVEL SECURITY;
