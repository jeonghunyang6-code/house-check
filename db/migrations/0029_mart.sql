-- 대형마트 (카카오 지도 '대형마트 > 브랜드' 분류, 입지톡 커넥터로 수집 — 커넥터는 대화 세션에서만 쓸 수 있어
-- 원본 TSV 는 저장소에 두지 않고 jobs/infra.py mart --file 로 넣는다). 설명용, 점수화하지 않음(M3)
CREATE TABLE IF NOT EXISTS mart (
  place_id   TEXT PRIMARY KEY,         -- 카카오 place id
  name       TEXT NOT NULL,
  brand      TEXT,                     -- 이마트·홈플러스·롯데마트·코스트코코리아·트레이더스 홀세일 클럽·킴스클럽
  lat        DOUBLE PRECISION NOT NULL,
  lng        DOUBLE PRECISION NOT NULL,
  collected  DATE NOT NULL
);
ALTER TABLE mart ENABLE ROW LEVEL SECURITY;
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS mart_name TEXT,     -- 가장 가까운 대형마트 (직선, 5km 안)
  ADD COLUMN IF NOT EXISTS mart_m    INTEGER;
