-- H5 정비사업 단계 (서울, collector/redev.py, jobs/redev.py, redev.yml 매주). 서울 열린데이터광장 OA-22856 TbSeoulRedevStatus 전체를 덮어쓴다
CREATE TABLE IF NOT EXISTS redev_zone (
  code             TEXT PRIMARY KEY,
  region_code      TEXT,
  district         TEXT,
  zone_nm          TEXT,
  jibun_addr       TEXT,
  road_addr        TEXT,
  umd_name         TEXT,       -- 지번 주소에서 읽은 법정동
  bun              INTEGER,
  ji               INTEGER,
  public_private   TEXT,       -- 민간 | 공공
  general_promoted TEXT,       -- 일반 | 재촉(재정비촉진)
  biz_type         TEXT,       -- 주택정비형 재개발 | 도시정비형 재개발 | 공동주택재건축 | 아파트지구재건축 | 단독주택재건축
  stage            TEXT,       -- 구역지정 | 추진위 | 조합설립 | 사업시행 | 관리처분 | 착공 | …
  stage_no         SMALLINT,   -- collector/redev.py STAGE_ORDER 순서 (모르는 단계는 NULL)
  existing_hh      INTEGER,
  built_hh         INTEGER,
  sale_hh          INTEGER,
  rent_hh          INTEGER,
  zone_ymd         DATE,       -- 구역지정(최초)
  committee_ymd    DATE,       -- 추진위원회 승인
  assoc_ymd        DATE,       -- 조합설립인가
  impl_ymd         DATE,       -- 사업시행인가(최초)
  mgmt_ymd         DATE,       -- 관리처분인가(최초)
  migration_ymd    DATE,       -- 이주 시작
  construction_ymd DATE,       -- 착공
  fetched_at       DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS complex_redev (
  apt_seq TEXT NOT NULL,
  code    TEXT NOT NULL,
  how     TEXT NOT NULL CHECK (how IN ('jibun', 'name')),
  PRIMARY KEY (apt_seq, code)
);
ALTER TABLE redev_zone ENABLE ROW LEVEL SECURITY;
ALTER TABLE complex_redev ENABLE ROW LEVEL SECURITY;
