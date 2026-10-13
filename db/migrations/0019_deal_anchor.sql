-- 저장 구조 C (2026-10-14): 매매 원본은 최근 2년만 DB 에 두고 그 이전은 Releases 의 deals_YYYYMM.csv.gz.
-- 과거가 필요한 값은 보관 파일에서 한 번 계산해 둔다 (collector/deal_anchor.py, jobs/deal_archive.py anchor → load)
CREATE TABLE IF NOT EXISTS deal_anchor (
  apt_seq         TEXT    NOT NULL,
  area_group      INTEGER NOT NULL,
  hist_high_10k   INTEGER NOT NULL,   -- 보관 구간 최고가 (중개·비해제)
  hist_high_date  DATE    NOT NULL,
  peak_10k        INTEGER,            -- B2 전고점: 2021-01~2022-06 월별 기준 시세 최고
  peak_m          TEXT,
  trough_10k      INTEGER,            -- B2 저점: 2022-07~2023-06 최저
  trough_m        TEXT,
  p20_10k         INTEGER,            -- A6 2020년 1분기 중앙값
  PRIMARY KEY (apt_seq, area_group)
);
CREATE TABLE IF NOT EXISTS deal_region_month (
  region_code    TEXT    NOT NULL,
  contract_month TEXT    NOT NULL,
  n_all          INTEGER NOT NULL,
  n_broker       INTEGER NOT NULL,
  n_direct       INTEGER NOT NULL,
  n_cancelled    INTEGER NOT NULL,
  p84_median_10k INTEGER,             -- 전용 84~85㎡(area_group) 중개 중앙값
  PRIMARY KEY (region_code, contract_month)
);
