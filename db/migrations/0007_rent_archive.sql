-- 전월세 저장 방식 (docs/HANDOFF.md 0절 "저장 방식"): 원본은 GitHub Releases 의 월별 CSV.gz, DB 에는 요약만.
-- 요약 단위: 단지 × 면적군 × 계약월. 지표 D1(전세가율)·D3(역전세)·D5(신규 전세·갱신 비중)의 재료.
-- 여러 달을 묶은 정확한 중앙값이 필요하면 배치가 원본 파일을 읽는다(월별 중앙값끼리는 합칠 수 없다).
CREATE TABLE IF NOT EXISTS rent_monthly (
  apt_seq               TEXT    NOT NULL,
  area_group            INTEGER NOT NULL,     -- FLOOR(전용면적)
  contract_month        TEXT    NOT NULL CHECK (contract_month ~ '^[0-9]{6}$'),
  region_code           TEXT    NOT NULL,
  apt_name              TEXT    NOT NULL,
  n_jeonse              INTEGER NOT NULL,     -- 월세 0
  jeonse_median_10k     INTEGER,
  n_jeonse_new          INTEGER NOT NULL,     -- 계약구분 '신규' 전세
  jeonse_new_median_10k INTEGER,
  n_jeonse_renew        INTEGER NOT NULL,     -- 계약구분 '갱신' 전세
  n_wolse               INTEGER NOT NULL,
  wolse_deposit_median_10k INTEGER,
  wolse_rent_median_10k    INTEGER,
  n_renewal_right_used  INTEGER NOT NULL,     -- 갱신요구권 사용 (전세·월세 합)
  n_type_blank          INTEGER NOT NULL,     -- 계약구분 공백
  PRIMARY KEY (apt_seq, area_group, contract_month)
);
CREATE INDEX IF NOT EXISTS rent_monthly_region_month_idx ON rent_monthly (region_code, contract_month);

-- 원본 파일에 무엇이 들어 있는지. 과거 이력 이어받기(건너뛰기)와 확인용.
CREATE TABLE IF NOT EXISTS archive_cells (
  kind           TEXT NOT NULL CHECK (kind IN ('trade', 'rent')),
  region_code    TEXT NOT NULL,
  contract_month TEXT NOT NULL CHECK (contract_month ~ '^[0-9]{6}$'),
  n_rows         INTEGER NOT NULL,
  source         TEXT NOT NULL CHECK (source IN ('api_backfill', 'db_rollover')),
  archived_at    DATE NOT NULL,
  asset_name     TEXT NOT NULL,                -- 예: rents_202301.csv.gz
  PRIMARY KEY (kind, region_code, contract_month)
);

ALTER TABLE rent_monthly  ENABLE ROW LEVEL SECURITY;
ALTER TABLE archive_cells ENABLE ROW LEVEL SECURITY;
