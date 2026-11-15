-- 새로 생기는 역(가칭) 좌표: collector/projects.py geo_stations 의 주소를 GitHub 자동 작업(station_geo.yml)이
-- 네이버 클라우드 Geocoding 으로 찾아 둔다. jobs/policy.py 가 transit_projects.new_stations 를 만들 때 합친다(2026-11-15 사용자 요청)
CREATE TABLE IF NOT EXISTS station_geo (
  addr        TEXT PRIMARY KEY,          -- 찾은 주소(projects.py 에 적은 그대로)
  lat         DOUBLE PRECISION,          -- 못 찾으면 NULL
  lng         DOUBLE PRECISION,
  road        TEXT,                      -- Geocoding 이 돌려준 도로명 주소(확인용)
  geocoded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE station_geo ENABLE ROW LEVEL SECURITY;
