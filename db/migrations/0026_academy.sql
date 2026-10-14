-- 학원·교습소 (나이스 acaInsTiInfo, collector/neis.py). 좌표가 없어 법정동(읍·면) 단위로 센다. 설명용, 점수화하지 않음
CREATE TABLE IF NOT EXISTS academy_dong (
  sido        TEXT NOT NULL,      -- '서울'
  sgg         TEXT NOT NULL,      -- 주소에 적힌 시군구 '강남구', '수원시 영통구'
  dong        TEXT NOT NULL,      -- 법정동 또는 읍·면 '대치동'
  n           INTEGER NOT NULL,   -- 개원 중인 학원+교습소 전체
  exam        INTEGER NOT NULL,   -- 그중 '입시.검정 및 보습'
  exam_hagwon INTEGER NOT NULL,   -- 그중 학원(교습소 제외)
  loaded_at   DATE NOT NULL,
  PRIMARY KEY (sido, sgg, dong)
);
ALTER TABLE academy_dong ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS academy_exam   INTEGER,   -- 같은 법정동 입시·보습 학원+교습소 수
  ADD COLUMN IF NOT EXISTS academy_hagwon INTEGER;   -- 그중 학원
