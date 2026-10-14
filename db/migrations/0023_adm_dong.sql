-- 행정동 경계 요약·인접 (jobs/geo.py boundary, collector/adjacency.py). 경계 원본(GeoJSON)은 Releases raw-data 의 hadm_<연도>.geojson.gz
CREATE TABLE IF NOT EXISTS adm_dong (
  adm_cd   TEXT PRIMARY KEY,           -- SGIS 행정동 코드 8자리 (complexes.adm_cd 와 같다)
  adm_nm   TEXT NOT NULL,              -- '서울특별시 송파구 풍납1동'
  year     TEXT NOT NULL,              -- 경계 기준 연도
  area_km2 DOUBLE PRECISION,
  cx       DOUBLE PRECISION,           -- 중심 (UTM-K, m)
  cy       DOUBLE PRECISION,
  han_side TEXT                        -- 한강 N/S (모르면 NULL)
);
CREATE TABLE IF NOT EXISTS adm_adjacent (
  a           TEXT NOT NULL,           -- a < b
  b           TEXT NOT NULL,
  shared      INTEGER NOT NULL,        -- 함께 쓰는 20m 칸 수 (맞닿은 경계 길이에 비례)
  cross_river BOOLEAN NOT NULL,        -- 한강을 사이에 둠
  PRIMARY KEY (a, b)
);
ALTER TABLE adm_dong     ENABLE ROW LEVEL SECURITY;
ALTER TABLE adm_adjacent ENABLE ROW LEVEL SECURITY;
