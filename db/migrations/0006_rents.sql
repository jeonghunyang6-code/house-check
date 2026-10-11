-- 전월세 스냅샷 (매매 deals 와 같은 방식, collector/pg_store.py). 필드는 2026-10-11 실제 응답으로 확인.
-- 전월세에는 해제 개념이 없어 is_cancelled 가 없다. 이벤트는 registered | disappeared 만.
CREATE TABLE IF NOT EXISTS rents (
  rent_key             TEXT PRIMARY KEY,      -- 단지일련번호|계약일|면적|층|보증금|월세#순번
  apt_seq              TEXT NOT NULL,
  apt_name             TEXT NOT NULL,
  region_code          TEXT NOT NULL,
  contract_month       TEXT NOT NULL,         -- YYYYMM
  contract_date        DATE NOT NULL,
  area_m2              NUMERIC(7,2) NOT NULL,
  area_group           INTEGER GENERATED ALWAYS AS (FLOOR(area_m2)::INTEGER) STORED,
  floor                INTEGER,
  deposit_10k          INTEGER NOT NULL,      -- 만원
  monthly_rent_10k     INTEGER NOT NULL,      -- 만원, 0 이면 전세
  contract_type        TEXT CHECK (contract_type IN ('신규', '갱신')),  -- 응답 공백이면 NULL
  used_renewal_right   BOOLEAN NOT NULL,
  term_start           DATE,                  -- 계약기간 시작 월 1일
  term_end             DATE,
  pre_deposit_10k      INTEGER,
  pre_monthly_rent_10k INTEGER,
  first_seen_date      DATE,
  last_seen_date       DATE NOT NULL,
  disappeared          BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS rents_complex_idx ON rents (apt_seq, area_group, contract_date);
CREATE INDEX IF NOT EXISTS rents_region_month_idx ON rents (region_code, contract_month);

CREATE TABLE IF NOT EXISTS rent_events (
  id         BIGSERIAL PRIMARY KEY,
  rent_key   TEXT NOT NULL REFERENCES rents (rent_key),
  event      TEXT NOT NULL CHECK (event IN ('registered', 'disappeared')),
  event_date DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS rent_events_date_idx ON rent_events (event_date, event);

ALTER TABLE rents       ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_events ENABLE ROW LEVEL SECURITY;

-- 수집 기록에 종류(trade | rent)를 넣는다. 기존 행은 모두 매매.
ALTER TABLE snapshot_runs ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'trade' CHECK (kind IN ('trade', 'rent'));
ALTER TABLE snapshot_runs DROP CONSTRAINT IF EXISTS snapshot_runs_pkey;
ALTER TABLE snapshot_runs ADD PRIMARY KEY (kind, region_code, contract_month, run_date);
DROP INDEX IF EXISTS snapshot_runs_region_date_idx;
CREATE INDEX IF NOT EXISTS snapshot_runs_kind_region_date_idx ON snapshot_runs (kind, region_code, run_date);
