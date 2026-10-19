-- H5 대지면적 보충: VWorld 토지특성(사용자 PC 에서 tools/pc/vworld_land.py 로 받은 결과, 2026-10-19 11,036필지).
-- 단지 대표 지번 한 필지라 여러 필지에 걸친 단지는 작게 잡힌다 → complex_bldg 대지면적과 비교해 쓴다
CREATE TABLE IF NOT EXISTS land_parcel (
  pnu          TEXT PRIMARY KEY,    -- 법정동 10 + 일반/산 1 + 본번 4 + 부번 4
  stdr_year    TEXT,
  land_area    NUMERIC(12, 2),      -- ㎡
  jimok        TEXT,
  use_zone     TEXT,                -- 용도지역 (제3종일반주거지역 등)
  price_per_m2 INTEGER,             -- 개별공시지가 원/㎡
  loaded_at    DATE NOT NULL
);
ALTER TABLE land_parcel ENABLE ROW LEVEL SECURITY;
