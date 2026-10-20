-- 직장까지 자차 시간 (collector/drive.py, jobs/drive.py, drive.yml). 네이버 클라우드 Maps Directions 5(실시간 빠른길).
-- 출발 시각을 정하는 옵션이 없어 출근 시간대(평일 아침)에 돌려 그때 교통을 담는다
CREATE TABLE IF NOT EXISTS complex_drive (
  apt_seq    TEXT NOT NULL,
  dest       TEXT NOT NULL,          -- collector/drive.py DESTS 키
  minutes    NUMERIC(6, 1),          -- 소요 시간(분). 경로를 못 찾으면 NULL
  km         NUMERIC(6, 1),
  fetched_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (apt_seq, dest)
);
ALTER TABLE complex_drive ENABLE ROW LEVEL SECURITY;
