-- 입주 예정 물량 공식 자료 (한국부동산원 주택공급정보, 공공데이터포털 15111714). 세대수 = 조합원·임대 포함 총 세대
-- F1(sql/metrics.sql 8)은 이 자료가 다루는 입주 월 범위 안에서는 이 표만, 범위 밖은 presale 를 쓴다
CREATE TABLE IF NOT EXISTS ipju_plan (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  address     TEXT NOT NULL,
  area        TEXT NOT NULL,        -- 서울·경기·인천
  kind        TEXT,                 -- 분양 / 임대 / 분양임대
  households  INTEGER NOT NULL,
  move_in_ym  TEXT NOT NULL,        -- YYYYMM
  region_code TEXT,
  lifezone_id TEXT,
  locate_by   TEXT,                 -- presale(청약홈 공고 좌표) / dong(같은 법정동 단지들)
  file_name   TEXT NOT NULL,        -- 원본 파일 이름(기준일 포함)
  loaded      DATE NOT NULL
);
ALTER TABLE ipju_plan ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS ipju_plan_move_in_idx ON ipju_plan (move_in_ym);
