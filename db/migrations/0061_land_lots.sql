-- H5 여러 필지 단지: 건축물대장 부속 지번(getBrAtchJibunInfo) → 단지 × 필지. VWorld 면적(land_parcel)을 대표 필지와 합친다
-- (2026-10-19 목동신시가지5·7·9·11·13 은 대표 필지만이라 용적률 190~232% 로 나왔다, 알려진 값 약 120~160%)
CREATE TABLE IF NOT EXISTS complex_land_lot (
  apt_seq TEXT NOT NULL,
  pnu     TEXT NOT NULL,
  PRIMARY KEY (apt_seq, pnu)
);
CREATE TABLE IF NOT EXISTS complex_atch_done (
  apt_seq    TEXT PRIMARY KEY,
  n_lots     INTEGER,           -- 부속 지번 수 (NULL = 지번을 못 읽음)
  fetched_at DATE NOT NULL
);
ALTER TABLE complex_land_lot ENABLE ROW LEVEL SECURITY;
ALTER TABLE complex_atch_done ENABLE ROW LEVEL SECURITY;

-- complex_rebuild 다시: 대지면적 = 건축물대장 > VWorld 대표 필지 + 부속 필지 합
DROP VIEW IF EXISTS complex_rebuild;
CREATE VIEW complex_rebuild AS
WITH c AS (
  SELECT c.apt_seq, c.build_year, k.households,
    c.bjd_code || '1' || lpad(split_part(c.jibun, '-', 1), 4, '0') || lpad(coalesce(nullif(split_part(c.jibun, '-', 2), ''), '0'), 4, '0') AS pnu,
    b.plat_area, b.vl_rat, b.estm_area, b.hhld
  FROM complexes c LEFT JOIN complex_bldg b USING (apt_seq) LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
  WHERE c.jibun ~ '^[0-9]+(-[0-9]+)?$' AND c.bjd_code ~ '^[0-9]{10}$'
), lots AS (   -- 대표 필지가 아닌 부속 필지
  SELECT c.apt_seq, count(*) AS n_atch, count(l.pnu) AS n_have, sum(l.land_area) AS atch_area
  FROM c JOIN complex_land_lot x USING (apt_seq) LEFT JOIN land_parcel l ON l.pnu = x.pnu
  WHERE x.pnu <> c.pnu GROUP BY 1
), d AS (
  SELECT c.*, l.land_area AS vw_area, l.use_zone, l.price_per_m2, lots.n_atch, lots.n_have,
    CASE WHEN c.plat_area > 0 THEN c.plat_area WHEN l.land_area > 0 THEN l.land_area + coalesce(lots.atch_area, 0) END AS land_area,
    CASE WHEN c.plat_area > 0 THEN '건축물대장'
         WHEN l.land_area > 0 AND coalesce(lots.n_atch, 0) = 0 THEN 'VWorld 대표 필지'
         WHEN l.land_area > 0 AND lots.n_have = lots.n_atch THEN 'VWorld 대표 + 부속 ' || lots.n_atch || '필지'
         WHEN l.land_area > 0 THEN 'VWorld 대표 + 부속 ' || lots.n_have || '/' || lots.n_atch || '필지(나머지 면적 미수집)' END AS land_src,
    CASE WHEN l.use_zone LIKE '제1종일반%' THEN 200 WHEN l.use_zone LIKE '제2종일반%' THEN 250 WHEN l.use_zone LIKE '제3종일반%' THEN 300
         WHEN l.use_zone LIKE '준주거%' THEN 500 END AS vl_cap,
    coalesce(nullif(c.households, 0), c.hhld) AS hh
  FROM c LEFT JOIN land_parcel l USING (pnu) LEFT JOIN lots USING (apt_seq)
), e AS (
  SELECT d.*, CASE WHEN d.vl_rat > 0 THEN d.vl_rat WHEN d.estm_area > 0 AND d.land_area > 0 THEN round(d.estm_area / d.land_area * 100, 1) END AS vl_raw
  FROM d
)
SELECT apt_seq, build_year, land_area, land_src, use_zone, price_per_m2, vl_cap, hh,
  (vl_cap IS NOT NULL AND vl_raw > vl_cap * 1.3) AS suspect,
  CASE WHEN NOT (vl_cap IS NOT NULL AND vl_raw > vl_cap * 1.3) THEN vl_raw END AS vl_rat,
  CASE WHEN NOT (vl_cap IS NOT NULL AND coalesce(vl_raw, 0) > vl_cap * 1.3) AND land_area > 0 AND hh > 0 THEN round(land_area / hh, 1) END AS land_per_hh
FROM e;
