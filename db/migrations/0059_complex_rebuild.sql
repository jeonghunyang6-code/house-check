-- H5 재건축 사업성 재료를 한데 모은 뷰 (건축물대장 complex_bldg + VWorld 대지면적 land_parcel + K-apt 세대수).
-- 대지면적: 건축물대장 총괄표제부 값이 있으면 그것, 없으면 VWorld 대표 필지 면적(2026-10-19 두 값이 다 있는 877곳 중 82%가 ±10% 안, 중앙값 비 1.00).
-- 대표 필지 하나만 잡혀 작게 나오는 단지(여러 필지)는 계산 용적률이 용도지역 법정 상한(국토계획법 시행령 제85조:
-- 1종 200·2종 250·3종 300·준주거 500%)의 🔧 1.3배를 넘으면 suspect 로 표시하고 용적률·대지지분을 비운다
CREATE OR REPLACE VIEW complex_rebuild AS
WITH c AS (
  SELECT c.apt_seq, c.build_year, k.households,
    c.bjd_code || '1' || lpad(split_part(c.jibun, '-', 1), 4, '0') || lpad(coalesce(nullif(split_part(c.jibun, '-', 2), ''), '0'), 4, '0') AS pnu,
    b.plat_area, b.vl_rat, b.estm_area, b.hhld
  FROM complexes c LEFT JOIN complex_bldg b USING (apt_seq) LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
  WHERE c.jibun ~ '^[0-9]+(-[0-9]+)?$' AND c.bjd_code ~ '^[0-9]{10}$'
), d AS (
  SELECT c.*, l.land_area AS vw_area, l.use_zone, l.price_per_m2,
    CASE WHEN c.plat_area > 0 THEN c.plat_area ELSE l.land_area END AS land_area,
    CASE WHEN c.plat_area > 0 THEN '건축물대장' WHEN l.land_area > 0 THEN 'VWorld 대표 필지' END AS land_src,
    CASE WHEN l.use_zone LIKE '제1종일반%' THEN 200 WHEN l.use_zone LIKE '제2종일반%' THEN 250 WHEN l.use_zone LIKE '제3종일반%' THEN 300
         WHEN l.use_zone LIKE '준주거%' THEN 500 END AS vl_cap,
    coalesce(nullif(c.households, 0), c.hhld) AS hh
  FROM c LEFT JOIN land_parcel l USING (pnu)
), e AS (
  SELECT d.*, CASE WHEN d.vl_rat > 0 THEN d.vl_rat WHEN d.estm_area > 0 AND d.land_area > 0 THEN round(d.estm_area / d.land_area * 100, 1) END AS vl_raw
  FROM d
)
SELECT apt_seq, build_year, land_area, land_src, use_zone, price_per_m2, vl_cap, hh,
  (vl_cap IS NOT NULL AND vl_raw > vl_cap * 1.3) AS suspect,
  CASE WHEN NOT (vl_cap IS NOT NULL AND vl_raw > vl_cap * 1.3) THEN vl_raw END AS vl_rat,
  CASE WHEN NOT (vl_cap IS NOT NULL AND coalesce(vl_raw, 0) > vl_cap * 1.3) AND land_area > 0 AND hh > 0 THEN round(land_area / hh, 1) END AS land_per_hh
FROM e;
