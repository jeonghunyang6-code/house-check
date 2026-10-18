-- 규제 이력 (collector/policy.py 가 원본, jobs/policy.py 가 통째로 다시 넣는다). 📖 토허제 p.269~270, 풍선효과 p.288~292
CREATE TABLE IF NOT EXISTS policy_zone (
  id          SERIAL PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('토허', '규제지역')),
  region_code TEXT NOT NULL,
  umd_name    TEXT,                 -- NULL = 시군구 전체
  start_date  DATE,                 -- NULL = 2020년 이전부터
  end_date    DATE,                 -- 마지막 유효일, NULL = 지금도 유효
  scope       TEXT NOT NULL CHECK (scope IN ('sgg', 'dong', 'part')),   -- part = 구역이 동의 일부만
  note        TEXT NOT NULL,
  source      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policy_events (
  event_date DATE NOT NULL,
  kind       TEXT NOT NULL,
  title      TEXT NOT NULL,
  source     TEXT NOT NULL,
  PRIMARY KEY (event_date, kind)
);
ALTER TABLE policy_zone ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_events ENABLE ROW LEVEL SECURITY;
