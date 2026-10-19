-- 단지 → 지역 B1 국면 (R-ONE 매매지수, jobs/market.py region_phase). 2026-10-20 단지 B1 백테스트(docs/insights/backtests.md)에서
-- 단지 실거래 라벨은 같은 구 단지 대비 예측력이 없어, 국면 '방향'은 지역 라벨을 쓴다(D4 매매 하락 원인, 시안 ⑦ 국면 필터·④).
-- 시군구가 R-ONE 에 없으면(양평·가평·연천·강화 등) 시도 값. 인천 시도는 50124(50024 는 비어 있음)
CREATE OR REPLACE VIEW complex_region_phase AS
WITH sgg AS (
  SELECT DISTINCT ON (r.region_code) r.region_code, r.name, p.phase, p.chg_12m, p.asof
  FROM rone_regions r JOIN region_phase p ON p.cls_id = r.cls_id AND p.stat = 'sale'
  WHERE r.region_code IS NOT NULL AND p.phase IS NOT NULL
  ORDER BY r.region_code, p.asof DESC, r.cls_id DESC
), sido AS (
  SELECT s.sido, s.name, p.phase, p.chg_12m, p.asof
  FROM (VALUES ('11', 50008, '서울'), ('28', 50124, '인천'), ('41', 50016, '경기')) AS s (sido, cls_id, name)
  JOIN region_phase p ON p.cls_id = s.cls_id AND p.stat = 'sale'
)
SELECT c.apt_seq, coalesce(g.name, s.name) AS region_name, coalesce(g.phase, s.phase) AS phase,
  coalesce(g.chg_12m, s.chg_12m) AS chg_12m, coalesce(g.asof, s.asof) AS asof, (g.region_code IS NULL) AS sido_level
FROM complexes c
LEFT JOIN sgg g ON g.region_code = c.region_code
LEFT JOIN sido s ON s.sido = left(c.region_code, 2)
WHERE coalesce(g.phase, s.phase) IS NOT NULL;
