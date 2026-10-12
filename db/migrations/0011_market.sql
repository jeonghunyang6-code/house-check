-- 시장 국면·체크리스트 신호 (collector/market.py, jobs/market.py). 정의: docs/insights/indicators.md B1·B3·B4·B5, 3절 반등 신호.

-- 주간 상승·하락 지역 수 (B4 ①, B5 ①). 전국 시군구를 다 저장하지 않고 주마다 집계만 남긴다 (jobs/rone.py).
CREATE TABLE IF NOT EXISTS rone_breadth (
  stat      TEXT    NOT NULL CHECK (stat IN ('sale', 'jeonse')),
  week_id   TEXT    NOT NULL,
  week_date DATE    NOT NULL,
  scope     TEXT    NOT NULL CHECK (scope IN ('전국', '수도권')),
  n         INTEGER NOT NULL,   -- 말단 지역(시군구) 수
  n_up      INTEGER NOT NULL,   -- 직전 주 대비 상승
  n_down    INTEGER NOT NULL,   -- 직전 주 대비 하락
  PRIMARY KEY (stat, week_id, scope)
);

-- 지역 국면 (B1) + 고점 대비 낙폭 (B3). 최신 주 기준으로 덮어쓴다.
CREATE TABLE IF NOT EXISTS region_phase (
  stat        TEXT    NOT NULL CHECK (stat IN ('sale', 'jeonse')),
  cls_id      INTEGER NOT NULL,
  asof        DATE    NOT NULL,   -- 최신 주
  chg_12m     NUMERIC(6, 2),      -- 12개월 누적 변화 %
  up_months   INTEGER,            -- 최근 12개월 중 상승한 달
  down_months INTEGER,
  last3       TEXT CHECK (last3 IN ('상승', '하락', '혼조')),
  phase       TEXT,               -- 상승장 | 하락장 | 보합장 | 일시 반등 | 일시 조정 | 추세 불명확
  drawdown    NUMERIC(6, 2),      -- 최근 24개월 최고 대비 낙폭 % (B3)
  PRIMARY KEY (stat, cls_id)
);

-- 홈 체크리스트 신호. key 별 최신 값만 둔다.
CREATE TABLE IF NOT EXISTS market_signals (
  key     TEXT PRIMARY KEY,       -- 예: b4_down_ratio, b4_jeonse_8w, supply_seoul
  asof    DATE NOT NULL,
  value   NUMERIC,
  state   TEXT,                   -- 충족 | 미충족 | 데이터 없음 | 상승장 등
  detail  TEXT
);

ALTER TABLE rone_breadth   ENABLE ROW LEVEL SECURITY;
ALTER TABLE region_phase   ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_signals ENABLE ROW LEVEL SECURITY;
