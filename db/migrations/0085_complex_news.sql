-- 관심 단지 소식(jobs/complex_news.py, collector/complex_news.py). 상세 탭 맨 아래 '단지 소식', 금요일 주간 요약(2026-11-15 사용자 요청)
-- 기사 본문은 저장하지 않는다: 제목·링크·날짜·언론사·딱지만. 200일 지나면 지움
CREATE TABLE IF NOT EXISTS complex_news (
  apt_seq    TEXT NOT NULL,
  url        TEXT NOT NULL,
  title      TEXT NOT NULL,
  outlet     TEXT,
  pub        DATE NOT NULL,
  in_title   BOOLEAN NOT NULL DEFAULT false,   -- 제목에 단지 이름(아니면 요약문에만)
  tags       TEXT,                             -- 쉼표로: 리모델링,시공사
  first_seen DATE NOT NULL,
  PRIMARY KEY (apt_seq, url)
);
CREATE INDEX IF NOT EXISTS complex_news_pub ON complex_news (apt_seq, pub);
ALTER TABLE complex_news ENABLE ROW LEVEL SECURITY;
