-- 분양권·입주권 거래 (국토부 RTMSDataSvcSilvTrade, jobs/right_deals.py). 신축·재건축 단지는 등기 전까지 매매(deals)에 안 나오고 여기로만 신고된다.
-- apt_seq 는 이름(단지·K-apt, 띄어쓰기·괄호 무시) 또는 같은 동·지번으로 붙인다. 못 붙인 거래는 NULL
CREATE TABLE IF NOT EXISTS right_deals (
  deal_key        TEXT PRIMARY KEY,      -- 시군구|이름(띄어쓰기 뺌)|계약일|면적|층|가격#같은 달 같은 값 순번
  region_code     TEXT NOT NULL,
  apt_name        TEXT NOT NULL,
  apt_seq         TEXT,
  umd_name        TEXT,
  jibun           TEXT,
  contract_date   DATE NOT NULL,
  area_m2         NUMERIC(7, 2) NOT NULL,
  area_group      INT NOT NULL,
  floor           INT,
  price_10k       INT NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('입주권', '분양권')),
  deal_type       TEXT NOT NULL,
  is_cancelled    BOOLEAN NOT NULL DEFAULT false,
  cancel_date     DATE,
  first_seen_date DATE NOT NULL DEFAULT ((now() AT TIME ZONE 'Asia/Seoul')::date),
  last_seen_date  DATE NOT NULL DEFAULT ((now() AT TIME ZONE 'Asia/Seoul')::date)
);
CREATE INDEX IF NOT EXISTS right_deals_seq ON right_deals (apt_seq, contract_date);
CREATE INDEX IF NOT EXISTS right_deals_rc ON right_deals (region_code, contract_date);
ALTER TABLE right_deals ENABLE ROW LEVEL SECURITY;
