-- K-apt 상세 정보 (jobs/kapt.py detail, collector/kapt.py detail_row). 관리사무소가 입력한 값이라 틀린 곳이 있을 수 있다
-- (예: 헬리오시티 노선 "3호선, 8호선, 9호선" / 역 "송파역"). H1 역세권은 도보 시간 구간으로 판정 (📖 역까지 10분·700m p.220)
ALTER TABLE kapt_complexes
  ADD COLUMN IF NOT EXISTS subway_line    TEXT,     -- subwayLine  "3호선, 8호선, 9호선"
  ADD COLUMN IF NOT EXISTS subway_station TEXT,     -- subwayStation "송파역"
  ADD COLUMN IF NOT EXISTS walk_subway    TEXT,     -- kaptdWtimesub "5분이내", "5~10분이내" …
  ADD COLUMN IF NOT EXISTS walk_bus       TEXT,     -- kaptdWtimebus
  ADD COLUMN IF NOT EXISTS parking_ground INTEGER,  -- kaptdPcnt  지상 주차 대수
  ADD COLUMN IF NOT EXISTS parking_under  INTEGER,  -- kaptdPcntu 지하 주차 대수
  ADD COLUMN IF NOT EXISTS ev_charger     INTEGER,  -- groundElChargerCnt + undergroundElChargerCnt
  ADD COLUMN IF NOT EXISTS cctv           INTEGER,  -- kaptdCccnt
  ADD COLUMN IF NOT EXISTS welfare        TEXT,     -- welfareFacility 부대·복리시설
  ADD COLUMN IF NOT EXISTS detail_at      DATE;     -- 상세 정보를 받은 날 (NULL 이면 아직)
