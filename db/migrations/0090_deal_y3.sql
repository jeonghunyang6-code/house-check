-- C12 3년 비교 (송희구 ▶ 언젠가는 옵니다 1:21 "6개월~1년 말고 적어도 3년", ▶ 호가가 비쌀 때 3:08 "몇 년 전 가격 차이가 지금도 유지되나").
-- 3년 전 같은 6개월(계약월 이번 달 −42 ~ −37개월)의 매매 중앙값. 원본은 보관 파일(deals_YYYYMM.csv.gz)에만 있어
-- jobs/deal_archive.py y3 가 매일 확인하고 창이 바뀐 달(한 달에 한 번)만 다시 계산한다. sql/metrics.sql 12) 가 최근 6개월과 비교
CREATE TABLE IF NOT EXISTS deal_y3 (
  apt_seq     TEXT NOT NULL,
  area_group  INTEGER NOT NULL,
  from_month  TEXT NOT NULL,
  to_month    TEXT NOT NULL,
  n           INTEGER NOT NULL,
  median_10k  INTEGER NOT NULL,
  PRIMARY KEY (apt_seq, area_group)
);
ALTER TABLE deal_y3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS m6_10k         INTEGER;       -- 최근 6개월(이번 달 −6 ~ −1) 중개·비해제·1층 제외 중앙값
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS m6_n           INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS y3_10k         INTEGER;       -- 3년 전 같은 6개월 중앙값 (deal_y3)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS y3_n           INTEGER;
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS chg_36m        NUMERIC(6, 2); -- 두 기간 모두 🔧 3건 이상일 때 m6 ÷ y3 − 1 (%)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS region_chg_36m NUMERIC(6, 2); -- 같은 생활권·같은 면적군 chg_36m 중앙값(🔧 5곳 이상), 없으면 생활권 전체 면적
