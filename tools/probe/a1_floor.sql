-- 임시 측정(PR 전에 삭제): 최근 2년 84㎡ 중개 거래의 저층 할인과 A4 급매 판정 영향
\pset pager off
WITH b AS (
  SELECT apt_seq, area_group, date_trunc('quarter', contract_date) q, floor, price_10k FROM deals
  WHERE NOT is_cancelled AND NOT disappeared AND deal_type = '중개' AND area_group BETWEEN 80 AND 85 AND floor IS NOT NULL
), hi AS (SELECT apt_seq, area_group, q, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) h, count(*) n FROM b WHERE floor >= 5 GROUP BY 1,2,3),
lo AS (SELECT apt_seq, area_group, q, CASE WHEN floor = 1 THEN '1' WHEN floor = 2 THEN '2' WHEN floor <= 4 THEN '3~4' ELSE '5+' END f,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) l FROM b WHERE floor BETWEEN 1 AND 4 GROUP BY 1,2,3,4)
SELECT f, count(*) n, round(percentile_cont(0.5) WITHIN GROUP (ORDER BY l / h)::numeric, 3) ratio
FROM lo JOIN hi USING (apt_seq, area_group, q) WHERE hi.n >= 2 GROUP BY 1 ORDER BY 1;
-- A4 와 같은 판정(서울 최근 8주, 직전 90일 중앙값 3건+, ×0.95 이하)을 층별로
WITH r AS (
  SELECT d.apt_seq, d.area_group, d.contract_date, d.price_10k, d.floor FROM deals d
  WHERE d.region_code LIKE '11%' AND NOT d.is_cancelled AND d.deal_type = '중개' AND d.contract_date > current_date - 56),
p AS (SELECT r.*, x.ref, x.n, x.ref1, x.n1 FROM r CROSS JOIN LATERAL (
  SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY b.price_10k) ref, count(*) n,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY b.price_10k) FILTER (WHERE b.floor <> 1) ref1,
         count(*) FILTER (WHERE b.floor <> 1) n1 FROM deals b
  WHERE b.apt_seq = r.apt_seq AND b.area_group = r.area_group AND NOT b.is_cancelled AND b.deal_type = '중개'
    AND b.contract_date < r.contract_date AND b.contract_date >= r.contract_date - 90) x)
SELECT CASE WHEN floor = 1 THEN '1' WHEN floor <= 4 THEN '2~4' ELSE '5+' END f,
  count(*) FILTER (WHERE n >= 3) total, count(*) FILTER (WHERE n >= 3 AND price_10k <= ref * 0.95) gm_now,
  count(*) FILTER (WHERE floor <> 1 AND n1 >= 3) total_ex1, count(*) FILTER (WHERE floor <> 1 AND n1 >= 3 AND price_10k <= ref1 * 0.95) gm_ex1
FROM p GROUP BY ROLLUP (1) ORDER BY 1;
