-- E6 갈아타기 목표 후보 (collector/gap.py, jobs/gap.py). 단지마다 1.5~2.5배·10km 안 단지 중 지금 격차가 5년 중 좁은 순 5곳
CREATE TABLE IF NOT EXISTS e6_targets (
  apt_seq      TEXT NOT NULL,
  rank         INTEGER NOT NULL,
  target_seq   TEXT NOT NULL,
  ratio_now    NUMERIC(6, 3) NOT NULL,   -- 마지막 분기 목표 ÷ 지금 (84㎡ 분기 중앙가)
  gap_now_10k  INTEGER NOT NULL,         -- 목표 − 지금 (만원)
  gap_pct      NUMERIC(5, 1) NOT NULL,   -- 함께 거래된 분기 격차 중 지금 이하 비율 (%), 낮을수록 좁아진 때
  n_q          INTEGER NOT NULL,
  dist_m       INTEGER NOT NULL,
  last_q       TEXT NOT NULL,
  asof         DATE NOT NULL,
  PRIMARY KEY (apt_seq, rank)
);
ALTER TABLE e6_targets ENABLE ROW LEVEL SECURITY;
