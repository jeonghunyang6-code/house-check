-- 정비구역 좌표(jobs/redev_geo.py). 같은 동·지번 단지 좌표 → 안 되면 네이버 클라우드 Geocoding(대표 지번). 상세 탭 실제 지도에 표시
ALTER TABLE redev_zone ADD COLUMN IF NOT EXISTS lat NUMERIC(9, 6);
ALTER TABLE redev_zone ADD COLUMN IF NOT EXISTS lng NUMERIC(9, 6);
ALTER TABLE redev_zone ADD COLUMN IF NOT EXISTS geo_src TEXT;   -- 'complex' | 'ncp' | 'none'
