-- 실거래 스냅샷 (docs/ARCHITECTURE.md 4.1, 6). Postgres 용. 실제 DB에 적용해보지 않았다.
-- 필드는 2026-10-11 국토부 매매 API 실제 응답으로 확인한 것만 쓴다 (collector/sources/molit.py 참고).

CREATE TABLE IF NOT EXISTS deals (
  deal_key        TEXT PRIMARY KEY,          -- 단지일련번호|계약일|면적|층|가격#동일키 순번 (collector/snapshot.py keyed)
  apt_seq         TEXT NOT NULL,             -- aptSeq. 예: 11680-279
  apt_name        TEXT NOT NULL,
  region_code     TEXT NOT NULL,             -- sggCd 시군구 5자리
  contract_month  TEXT NOT NULL,             -- YYYYMM (수집 단위)
  contract_date   DATE NOT NULL,
  area_m2         NUMERIC(7,2) NOT NULL,
  area_group      INTEGER GENERATED ALWAYS AS (FLOOR(area_m2)::INTEGER) STORED,
  floor           INTEGER NOT NULL,
  price_10k       INTEGER NOT NULL,          -- 만원
  deal_type       TEXT NOT NULL CHECK (deal_type IN ('중개', '직거래')),
  is_cancelled    BOOLEAN NOT NULL DEFAULT FALSE,
  cancel_date     DATE,
  rgst_date       DATE,                      -- 등기일 (신고일 아님)
  first_seen_date DATE,                      -- 처음 수집한 날. bootstrap 이면 NULL(미상)
  last_seen_date  DATE NOT NULL,
  disappeared     BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS deals_complex_idx ON deals (apt_seq, area_group, contract_date);
CREATE INDEX IF NOT EXISTS deals_region_month_idx ON deals (region_code, contract_month);
CREATE INDEX IF NOT EXISTS deals_first_seen_idx ON deals (first_seen_date);

CREATE TABLE IF NOT EXISTS deal_events (
  id         BIGSERIAL PRIMARY KEY,
  deal_key   TEXT NOT NULL REFERENCES deals (deal_key),
  event      TEXT NOT NULL CHECK (event IN ('registered', 'cancelled', 'disappeared')),
  event_date DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS deal_events_date_idx ON deal_events (event_date, event);
