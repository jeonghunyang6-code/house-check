-- B5 ② 과거 시계열 (jobs/b5_history.py, collector/b5.py). 경고선 백테스트용. 급지는 계산 시점의 최신 dong_grade 를 과거에도 그대로 쓴다(한계)
CREATE TABLE IF NOT EXISTS b5_history (
  month  TEXT    PRIMARY KEY CHECK (month ~ '^[0-9]{6}$'),  -- 계약월
  n_low  INTEGER NOT NULL,   -- 하위 급지(6~8급) 중개 거래 중 전고점 있는 것
  h_low  INTEGER NOT NULL,   -- 그중 신고가
  n_top  INTEGER NOT NULL,   -- 상위 급지(1~3급)
  h_top  INTEGER NOT NULL,
  n_lip  INTEGER NOT NULL,   -- 하위 급지 중 구축(20년+)·소단지(300세대 미만)
  h_lip  INTEGER NOT NULL,
  grade_asof DATE NOT NULL
);
