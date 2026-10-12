-- 단지 정보와 K-apt 연결 (collector/kapt.py, jobs/kapt.py).
-- 실거래의 단지일련번호(apt_seq)와 K-apt 단지코드(kapt_code) 사이에는 공통 키가 없다(2026-10-12 확인).
-- 실거래 응답의 법정동(sggCd+umdCd)·지번·도로명으로 K-apt 주소와 맞춘다.

-- 실거래 쪽 단지 (매일 수집·과거 이력에서 채운다)
CREATE TABLE IF NOT EXISTS complexes (
  apt_seq      TEXT PRIMARY KEY,
  apt_name     TEXT NOT NULL,
  region_code  TEXT NOT NULL,
  bjd_code     TEXT,             -- 법정동 10자리
  umd_name     TEXT,
  jibun        TEXT,
  road_addr    TEXT,             -- '삼성로 212'
  build_year   INTEGER,
  kapt_code    TEXT,             -- 연결된 K-apt 단지코드 (없으면 NULL)
  match_method TEXT CHECK (match_method IN ('jibun', 'road', 'name', 'manual')),
  updated_at   DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS complexes_bjd_idx ON complexes (bjd_code);
CREATE INDEX IF NOT EXISTS complexes_kapt_idx ON complexes (kapt_code);

-- K-apt 쪽 단지 (공동주택 단지 목록 + 기본 정보 V5)
CREATE TABLE IF NOT EXISTS kapt_complexes (
  kapt_code    TEXT PRIMARY KEY,
  kapt_name    TEXT NOT NULL,
  region_code  TEXT NOT NULL,
  bjd_code     TEXT,
  addr         TEXT,             -- 지번 주소 (kaptAddr)
  road_addr    TEXT,             -- 도로명 주소 (doroJuso)
  households   INTEGER,          -- kaptdaCnt 세대수
  use_date     DATE,             -- kaptUsedate 사용승인일
  dong_cnt     INTEGER,
  top_floor    INTEGER,
  builder      TEXT,
  heat_type    TEXT,             -- 지역난방 등
  sale_type    TEXT,             -- 분양·임대·혼합
  hh_lt60      INTEGER,          -- 전용 60㎡ 이하 세대수 (kaptMparea60)
  hh_60_85     INTEGER,
  hh_85_135    INTEGER,
  hh_gt135     INTEGER,
  listed_at    DATE NOT NULL,    -- 목록에서 마지막으로 본 날
  info_at      DATE              -- 기본 정보를 받은 날 (NULL 이면 아직)
);
CREATE INDEX IF NOT EXISTS kapt_bjd_idx ON kapt_complexes (bjd_code);

ALTER TABLE complexes      ENABLE ROW LEVEL SECURITY;
ALTER TABLE kapt_complexes ENABLE ROW LEVEL SECURITY;
