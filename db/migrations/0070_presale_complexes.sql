-- 분양 단지(입주·등기 전이라 우리 단지 목록 complexes 에 없는 곳): 분양권·입주권 거래(right_deals)를 시군구 + 이름(띄어쓰기·괄호 무시)으로 묶는다.
-- pc_seq = 'P' + 시군구 + '-' + 이름 해시 6자(다시 돌려도 같은 값). 나중에 complexes 에 생겨 거래가 연결되면 apt_seq 를 채운다(화면은 관심 ♡ 를 옮김)
CREATE TABLE IF NOT EXISTS presale_complexes (
  pc_seq      TEXT PRIMARY KEY,
  region_code TEXT NOT NULL,
  nkey        TEXT NOT NULL,           -- 정규화한 이름
  apt_name    TEXT NOT NULL,           -- 가장 최근 거래의 표기
  umd_name    TEXT,
  jibun       TEXT,
  apt_seq     TEXT,                    -- 연결된 실제 단지
  UNIQUE (region_code, nkey)
);
ALTER TABLE right_deals ADD COLUMN IF NOT EXISTS pc_seq TEXT;
CREATE INDEX IF NOT EXISTS right_deals_pc ON right_deals (pc_seq);
ALTER TABLE presale_complexes ENABLE ROW LEVEL SECURITY;
