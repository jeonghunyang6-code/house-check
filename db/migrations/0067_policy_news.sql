-- 정책 발표 후보 (collector/policy_news.py, jobs/policy_news.py). 기사 제목·요약문에서 '새로 결정된' 정책을 찾아 쌓는다.
-- 사람이 확인해 collector/policy.py 에 넣으면 status='added', 아니면 'ignored'. 정책 이력(policy_events)에는 자동으로 넣지 않는다
CREATE TABLE IF NOT EXISTS policy_news (
  kind        TEXT NOT NULL,          -- 토허·규제지역·대출·세금·공급
  first_date  DATE NOT NULL,          -- 결정 기사가 처음 나온 날
  n_press     INT  NOT NULL,          -- 결정 기사를 낸 서로 다른 언론사 수
  regions     TEXT,                   -- 두 기사 이상이 말한 시군구 코드(쉼표)
  articles    JSONB NOT NULL,         -- [{d, t, u}] 앞 몇 건
  known       TEXT,                   -- 이미 정책 이력에 있는 비슷한 사건(±10일)
  status      TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'added', 'ignored')),
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, first_date)
);
ALTER TABLE policy_news ENABLE ROW LEVEL SECURITY;
