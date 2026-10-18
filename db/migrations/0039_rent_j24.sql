-- D3 역전세: 24개월 전 ±1개월 전세 계약(신규·갱신) 보증금의 실제 중앙값. 원본은 보관 파일에만 있어
-- jobs/rent_archive.py daily 가 매일 파일로 다시 계산한다. sql/metrics.sql j24 는 이 표를 먼저 쓰고, 없으면 rent_monthly 근사
CREATE TABLE IF NOT EXISTS rent_j24 (
  apt_seq     TEXT NOT NULL,
  area_group  INTEGER NOT NULL,
  from_month  TEXT NOT NULL,
  to_month    TEXT NOT NULL,
  n           INTEGER NOT NULL,
  median_10k  INTEGER NOT NULL,
  PRIMARY KEY (apt_seq, area_group)
);
ALTER TABLE rent_j24 ENABLE ROW LEVEL SECURITY;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS jeonse_24m_approx BOOLEAN;  -- TRUE = rent_monthly 근사
