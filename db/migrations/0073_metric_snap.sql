-- 관심 단지 지표 주간 기록(jobs/notify.py weekly 가 금요일마다 쌓음). complex_metrics 는 매일 덮어써서 변화를 못 보므로 전세가율 4주 변화 등에 쓴다
CREATE TABLE IF NOT EXISTS metric_snap (
  apt_seq      TEXT NOT NULL,
  area_group   INT  NOT NULL,
  asof         DATE NOT NULL,
  ref_10k      INT,
  jeonse_10k   INT,
  jeonse_ratio NUMERIC(5, 1),
  PRIMARY KEY (apt_seq, area_group, asof)
);
ALTER TABLE metric_snap ENABLE ROW LEVEL SECURITY;
