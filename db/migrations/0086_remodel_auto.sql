-- 재건축·리모델링 단계 자동 갱신(collector/remodel.py, jobs/remodel.py, 2026-11-15 사용자 요청).
-- 손 관리 단계(collector/remodel.py REMODELS)보다 앞선 단계를 기사 제목으로 찾으면 여기 쌓는다. 틀리면 텔레그램 '빼줘' → status 'removed'
CREATE TABLE IF NOT EXISTS remodel_auto (
  apt_seq     TEXT NOT NULL,
  stage       TEXT NOT NULL,                 -- collector/remodel.py STAGES
  first_date  DATE NOT NULL,                 -- 처음 보도된 날
  n_press     INTEGER NOT NULL,
  press       TEXT,                          -- 언론사(쉼표)
  urls        JSONB,                         -- 기사 주소(최대 5)
  status      TEXT NOT NULL DEFAULT 'auto',  -- auto / removed
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (apt_seq, stage)
);
ALTER TABLE remodel_auto ENABLE ROW LEVEL SECURITY;
