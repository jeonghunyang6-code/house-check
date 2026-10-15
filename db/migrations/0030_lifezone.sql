-- 생활권 묶음 E0 (jobs/lifezone.py, collector/lifezone.py). 📖 지역 묶음 = 생활권 p.468~470
CREATE TABLE IF NOT EXISTS lifezone (
  zone_id   TEXT PRIMARY KEY,          -- 'Z0001' (단지 많은 순, 다시 만들면 바뀐다)
  name      TEXT NOT NULL,             -- 단지 많은 단위 3개: '잠실·석촌·잠실새내'
  units     TEXT NOT NULL,             -- 'S:역명' 또는 'D:행정동코드' (쉼표)
  n_complex INTEGER NOT NULL,
  built     DATE NOT NULL
);
ALTER TABLE lifezone ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS lifezone_id   TEXT,
  ADD COLUMN IF NOT EXISTS lifezone_name TEXT;
