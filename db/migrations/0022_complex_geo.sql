-- 단지 좌표 (jobs/geo.py, collector/sgis.py). SGIS 주소 → 좌표(WGS84). 법정동이 맞는 결과만 쓴다
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS lat        DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS lng        DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS adm_cd     TEXT,   -- SGIS 행정동 코드 8자리 (경계·인접 계산용)
  ADD COLUMN IF NOT EXISTS adm_nm     TEXT,
  ADD COLUMN IF NOT EXISTS geo_method TEXT,   -- jibun | road | kapt_road | none(못 찾음)
  ADD COLUMN IF NOT EXISTS geo_at     DATE;
