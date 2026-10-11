-- 일일 수집 기록. (시군구, 계약월)을 언제 몇 건 받았는지 남긴다.
-- jobs/daily.py 가 bootstrap 여부를 판단하는 데 쓴다: 처음 받는 칸이면서 그 시군구를 최근 3일 안에 받은 적이 없으면 bootstrap.
-- 수집이 끊겼다가 재개되면 그 사이 등록된 거래의 first_seen_date 는 재개일로 늦게 찍힌다(gap 으로 알 수 있음).
CREATE TABLE IF NOT EXISTS snapshot_runs (
  region_code    TEXT    NOT NULL,
  contract_month TEXT    NOT NULL CHECK (contract_month ~ '^[0-9]{6}$'),
  run_date       DATE    NOT NULL,
  n_deals        INTEGER NOT NULL,
  n_registered   INTEGER NOT NULL DEFAULT 0,
  n_cancelled    INTEGER NOT NULL DEFAULT 0,
  n_disappeared  INTEGER NOT NULL DEFAULT 0,
  bootstrap      BOOLEAN NOT NULL,
  PRIMARY KEY (region_code, contract_month, run_date)
);
CREATE INDEX IF NOT EXISTS snapshot_runs_region_date_idx ON snapshot_runs (region_code, run_date);
ALTER TABLE snapshot_runs ENABLE ROW LEVEL SECURITY;
