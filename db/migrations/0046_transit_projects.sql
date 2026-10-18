-- H4 호재 단계 (collector/projects.py 가 원본, jobs/policy.py 가 통째로 다시 넣는다). 📖 착공 후 들어가도 늦지 않다, 취소가 악재 p.279~280
CREATE TABLE IF NOT EXISTS transit_projects (
  name         TEXT PRIMARY KEY,
  status       TEXT NOT NULL CHECK (status IN ('계획', '확정', '착공', '개통', '예타탈락')),
  status_date  DATE,
  outlook      TEXT NOT NULL,
  cbd          TEXT,              -- 갈아타지 않고 내리는 업무지구(쉼표)
  region_codes TEXT NOT NULL,     -- 지나는 시군구(쉼표, 손으로 적음)
  source       TEXT NOT NULL
);
ALTER TABLE transit_projects ENABLE ROW LEVEL SECURITY;
