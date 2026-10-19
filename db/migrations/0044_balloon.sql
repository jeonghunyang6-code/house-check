-- 풍선효과 (📖 규제 지역 밖 비슷한 급지로 수요 이동 → 따라가지 마라 p.288~292). jobs/rone.py buyer, jobs/balloon.py
-- 1) 매입자 거주지별 아파트 매매 (R-ONE 월간). 경기는 시·구 둘 다 있다(region_codes 가 여러 개면 시 합계)
CREATE TABLE IF NOT EXISTS buyer_residence (
  period       TEXT NOT NULL CHECK (period ~ '^[0-9]{6}$'),
  grp_id       INTEGER NOT NULL,
  name         TEXT NOT NULL,          -- R-ONE 지역 경로 '경기>수원시>장안구'
  region_codes TEXT,                   -- 우리 시군구 코드(쉼표). 시도 합계·옛 구는 NULL
  total        INTEGER NOT NULL,
  same_sgg     INTEGER,                -- 같은 시군구 거주자
  same_sido    INTEGER,                -- 같은 시도 다른 시군구
  seoul        INTEGER,                -- 서울 거주자 (서울 지역은 0)
  other        INTEGER,                -- 그 밖 지역
  PRIMARY KEY (period, grp_id)
);
-- 2) 규제 사건별 시군구 비교 (토허 시군구 지정일 기준)
CREATE TABLE IF NOT EXISTS balloon (
  event_date    DATE NOT NULL,
  region_code   TEXT NOT NULL,
  grp           TEXT NOT NULL CHECK (grp IN ('inside', 'adjacent', 'far')),   -- 새로 규제 / 규제에 붙은 바깥 / 먼 바깥
  base_date     DATE NOT NULL,         -- 기준 주(사건 직전 발표 주)
  chg_4w NUMERIC(6, 2), chg_13w NUMERIC(6, 2), chg_26w NUMERIC(6, 2), chg_52w NUMERIC(6, 2),
  weeks_now     INTEGER NOT NULL,      -- 기준 주부터 마지막 발표 주까지
  chg_now       NUMERIC(6, 2),
  outsider_before NUMERIC(5, 1),       -- 외지인(다른 시군구 거주자) 매수 비중 %, 사건 전 6개월
  outsider_after  NUMERIC(5, 1),       -- 사건 달 다음 6개월(있는 만큼)
  seoul_before  NUMERIC(5, 1),         -- 서울 거주자 매수 비중 % (서울 밖 지역만)
  seoul_after   NUMERIC(5, 1),
  PRIMARY KEY (event_date, region_code)
);
CREATE TABLE IF NOT EXISTS balloon_path (
  event_date DATE NOT NULL,
  grp        TEXT NOT NULL,
  week       INTEGER NOT NULL,         -- 기준 주부터 몇 주
  median_chg NUMERIC(6, 2) NOT NULL,   -- 그 주 누적 변화 중앙값 (%)
  n          INTEGER NOT NULL,
  PRIMARY KEY (event_date, grp, week)
);
ALTER TABLE buyer_residence ENABLE ROW LEVEL SECURITY;
ALTER TABLE balloon ENABLE ROW LEVEL SECURITY;
ALTER TABLE balloon_path ENABLE ROW LEVEL SECURITY;
