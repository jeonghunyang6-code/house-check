-- R9 인지도 = 네이버 데이터랩 검색량 (collector/searchtrend.py, jobs/searchtrend.py, searchtrend.yml 매달). 기준 단지(헬리오시티) = 1
CREATE TABLE IF NOT EXISTS complex_search (
  apt_seq    TEXT PRIMARY KEY,
  keyword    TEXT NOT NULL,
  months     INTEGER NOT NULL,      -- 본 기간(달)
  n_months   INTEGER NOT NULL,      -- 값이 있는 달 수 (적으면 검색이 아주 적음)
  avg_ratio  NUMERIC(8, 3),         -- 같은 요청 안 상대값의 월평균
  idx        NUMERIC(8, 3),         -- 인지도 지수 = 단지 월평균 ÷ 기준 단지 월평균
  fetched_at DATE NOT NULL
);
ALTER TABLE complex_search ENABLE ROW LEVEL SECURITY;
