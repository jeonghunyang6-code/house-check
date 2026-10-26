-- 정비구역 단계 이력(jobs/redev.py 가 서울 매주·경기 파일 적재 뒤 쌓음). 처음 보는 (구역, 단계)면 한 줄.
-- 관심 단지 2km 안 구역의 단계가 바뀌면 jobs/notify.py daily 가 텔레그램으로 알리고 notified = true
CREATE TABLE IF NOT EXISTS redev_stage_hist (
  code       TEXT NOT NULL,
  stage      TEXT NOT NULL,
  stage_no   INT,
  first_seen DATE NOT NULL,
  notified   BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (code, stage)
);
