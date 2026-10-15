-- 업무지구 접근 H2 (jobs/infra.py access, collector/access.py). 📖 중심업무지구(사대문·여의도·강남) 연결, 어디서 내리는지 p.68~70, p.86~87
-- 단지: 가장 가까운 역까지 걷기(📖 700m = 10분 p.220) + 지하철 시간(표정속도) + 환승 🔧 5분/회. 버스·배차 대기 제외
ALTER TABLE complexes
  ADD COLUMN IF NOT EXISTS h2_cbd_min INTEGER, ADD COLUMN IF NOT EXISTS h2_cbd_tr SMALLINT,   -- 사대문(시청·광화문·종각·을지로입구·을지로3가·종로3가)
  ADD COLUMN IF NOT EXISTS h2_ybd_min INTEGER, ADD COLUMN IF NOT EXISTS h2_ybd_tr SMALLINT,   -- 여의도(여의도·여의나루·국회의사당·샛강)
  ADD COLUMN IF NOT EXISTS h2_gbd_min INTEGER, ADD COLUMN IF NOT EXISTS h2_gbd_tr SMALLINT;   -- 강남(강남·신논현·역삼·선릉·삼성·언주)
CREATE TABLE IF NOT EXISTS station_access (
  name    TEXT NOT NULL,      -- station.name
  lat     DOUBLE PRECISION NOT NULL,
  lng     DOUBLE PRECISION NOT NULL,
  cbd_min NUMERIC(5, 1), cbd_tr SMALLINT,
  ybd_min NUMERIC(5, 1), ybd_tr SMALLINT,
  gbd_min NUMERIC(5, 1), gbd_tr SMALLINT,
  built   DATE NOT NULL,
  PRIMARY KEY (name, lat, lng)
);
ALTER TABLE station_access ENABLE ROW LEVEL SECURITY;
