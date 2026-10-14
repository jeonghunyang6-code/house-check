-- 서울시 생활권계획 지역생활권(116)·권역생활권(5) ↔ 행정동 (jobs/geo.py lifezone). 생활권 묶음(E0) 교차검증용
-- 출처: 서울 열린데이터광장 OA-15527 「서울시 생활권계획 생활권경계 공간정보」(UPIS_SHP_ZON100, 공공누리 1유형)
CREATE TABLE IF NOT EXISTS seoul_lifezone (
  adm_cd     TEXT PRIMARY KEY,   -- SGIS 행정동 코드 (adm_dong)
  local_zone TEXT NOT NULL,      -- 지역생활권 '강남구_대치도곡'
  area_zone  TEXT,               -- 권역생활권 '동남권'
  method     TEXT NOT NULL       -- centroid (행정동 중심이 들어간 생활권)
);
ALTER TABLE seoul_lifezone ENABLE ROW LEVEL SECURITY;
