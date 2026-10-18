-- 지역 월별 지표 (jobs/region_stats.py). region = 우리 시군구 코드 / 시도 '11'·'28'·'41' / 'SUDO'(수도권) / 'KR'(전국)
--   jeonse_ratio  R-ONE (월) 중위 매매가격 대비 전세가격_아파트 (%) — D1 지역 평균, ▶ 60% 균형·50% 이하 투자 수요 유입 어려움·80~90% 조심 (J4)
--   sentiment     R-ONE 부동산시장 소비심리지수(국토연구원) — G7 보조, 시도·수도권·전국만
--   pop_total / pop_school(5~19세) / pop_working(15~64세) / pop_old(65세+)  KOSIS 주민등록인구 DT_1B04005N — H3 학령인구, D7 생산가능인구
--     인구는 해마다 12월 + 최근 25개월만 둔다
CREATE TABLE IF NOT EXISTS region_monthly (
  series  TEXT NOT NULL,
  region  TEXT NOT NULL,
  period  TEXT NOT NULL CHECK (period ~ '^[0-9]{6}$'),
  value   NUMERIC NOT NULL,
  PRIMARY KEY (series, region, period)
);
ALTER TABLE region_monthly ENABLE ROW LEVEL SECURITY;
