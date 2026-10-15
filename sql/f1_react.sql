-- F1 과거 입주 반응 (jobs/presale.py --react). 📖 입주 물량이 전세를 누른다 p.154, p.423, 입주장 5~6개월 p.55, 반응표 p.63.
-- 큰 입주(🔧 총 세대 500+, 2021-01 ~ 7개월 전)마다 같은 생활권 기존 단지(준공이 입주 2년 전 이전)의 전세 중앙가를
-- 입주 전 6개월(T-6~T-1) 평균 대비 입주 후 6개월(T~T+5) 평균으로 비교하고, 같은 시도 전체(그 생활권 제외)의 같은 비교를 뺀다(%p).
-- 단지·면적군마다 앞뒤 창에 거래가 다 있어야 하고(각 🔧 2건+), 생활권 쪽 🔧 5개 이상일 때만.
BEGIN;
DELETE FROM presale_react;
WITH ev AS (
  SELECT p.house_no, p.lifezone_id AS z, p.move_in_ym, to_date(p.move_in_ym, 'YYYYMM') AS t0, coalesce(p.total_hh, p.households) AS hh,
    CASE p.area WHEN '서울' THEN '11' WHEN '경기' THEN '41' WHEN '인천' THEN '28' END AS sd
  FROM presale p
  WHERE coalesce(p.total_hh, p.households) >= 500 AND p.lifezone_id IS NOT NULL
    AND p.move_in_ym BETWEEN '202101' AND to_char({TODAY} - INTERVAL '7 month', 'YYYYMM')
), r AS (
  SELECT rm.apt_seq, rm.area_group, to_date(rm.contract_month, 'YYYYMM') AS m, rm.jeonse_median_10k::numeric AS v, rm.n_jeonse AS n,
    c.lifezone_id AS z, left(rm.region_code, 2) AS sd, c.build_year
  FROM rent_monthly rm JOIN complexes c USING (apt_seq)
  WHERE rm.jeonse_median_10k > 0 AND rm.n_jeonse > 0 AND rm.contract_month >= '202007'
), pc AS (   -- 사건 × 단지·면적군: 앞뒤 창 평균
  SELECT e.house_no, r.apt_seq, r.area_group, (r.z = e.z) AS inz,
    sum(r.v * r.n) FILTER (WHERE r.m >= e.t0 - INTERVAL '6 month' AND r.m < e.t0) / nullif(sum(r.n) FILTER (WHERE r.m >= e.t0 - INTERVAL '6 month' AND r.m < e.t0), 0) AS pre,
    sum(r.v * r.n) FILTER (WHERE r.m >= e.t0 AND r.m < e.t0 + INTERVAL '6 month') / nullif(sum(r.n) FILTER (WHERE r.m >= e.t0 AND r.m < e.t0 + INTERVAL '6 month'), 0) AS post,
    sum(r.n) FILTER (WHERE r.m >= e.t0 - INTERVAL '6 month' AND r.m < e.t0) AS n_pre,
    sum(r.n) FILTER (WHERE r.m >= e.t0 AND r.m < e.t0 + INTERVAL '6 month') AS n_post
  FROM ev e JOIN r ON r.sd = e.sd AND r.m >= e.t0 - INTERVAL '6 month' AND r.m < e.t0 + INTERVAL '6 month'
    AND (r.build_year IS NULL OR r.build_year < extract(year FROM e.t0) - 1)
  GROUP BY 1, 2, 3, 4
), agg AS (
  SELECT house_no,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY post / pre) FILTER (WHERE inz) AS zr, count(*) FILTER (WHERE inz) AS zn,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY post / pre) FILTER (WHERE NOT inz) AS br
  FROM pc WHERE n_pre >= 2 AND n_post >= 2 AND pre > 0 GROUP BY 1
)
INSERT INTO presale_react (house_no, lifezone_id, move_in_ym, total_hh, zone_chg, base_chg, rel, n)
SELECT e.house_no, e.z, e.move_in_ym, e.hh, round(((a.zr - 1) * 100)::numeric, 2), round(((a.br - 1) * 100)::numeric, 2),
  round(((a.zr - a.br) * 100)::numeric, 2), a.zn
FROM ev e JOIN agg a USING (house_no) WHERE a.zn >= 5;
UPDATE lifezone SET f1_react_rel = NULL, f1_react_n = NULL;
UPDATE lifezone l SET f1_react_rel = round(v.r::numeric, 2), f1_react_n = v.n
FROM (SELECT lifezone_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY rel) AS r, count(*) AS n FROM presale_react GROUP BY 1) v
WHERE l.zone_id = v.lifezone_id;
COMMIT;
