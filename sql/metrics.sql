-- 단지 지표 계산 (jobs/metrics.py 가 {TODAY}·{PREV_DAYS}·{CUR_M}·{PREV_M} 를 채워 실행한다). 0010_metrics.sql 참고.
BEGIN;

-- 1) 최근 계약 거래의 전고점 (ARCHITECTURE 4.3: 이전 계약일의 중개·비해제 최고가)
UPDATE deals d SET prev_high_10k = (
  SELECT max(p.price_10k) FROM deals p
  WHERE p.apt_seq = d.apt_seq AND p.area_group = d.area_group AND p.contract_date < d.contract_date
    AND NOT p.is_cancelled AND p.deal_type = '중개')
WHERE d.contract_date >= {TODAY} - {PREV_DAYS};

-- 2) 단지 × 면적군 지표
DELETE FROM complex_metrics;
INSERT INTO complex_metrics
WITH base AS (
  SELECT apt_seq, area_group, contract_date, price_10k FROM deals WHERE NOT is_cancelled AND deal_type = '중개'
),
a1 AS (
  SELECT apt_seq, area_group,
    count(*) FILTER (WHERE contract_date > {TODAY} - 60)  AS n60,
    count(*) FILTER (WHERE contract_date > {TODAY} - 90)  AS n90,
    count(*) FILTER (WHERE contract_date > {TODAY} - 180) AS n180,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 60)  AS m60,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 90)  AS m90,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 180) AS m180,
    count(*) FILTER (WHERE contract_date > {TODAY} - 365) AS n_365,
    max(contract_date) AS last_date
  FROM base GROUP BY 1, 2
),
hi AS (
  SELECT DISTINCT ON (apt_seq, area_group) apt_seq, area_group, price_10k AS high_10k, contract_date AS high_date
  FROM base ORDER BY apt_seq, area_group, price_10k DESC, contract_date
),
months AS (SELECT generate_series(DATE '2021-01-01', DATE '2023-06-01', INTERVAL '1 month')::date AS m),
ref AS (  -- 월별 기준 시세 = 그 달 포함 3개월 이동 중앙값 (B1·B2)
  SELECT b.apt_seq, b.area_group, mo.m, percentile_cont(0.5) WITHIN GROUP (ORDER BY b.price_10k) AS v
  FROM months mo JOIN base b ON b.contract_date >= mo.m - INTERVAL '2 month' AND b.contract_date < mo.m + INTERVAL '1 month'
  GROUP BY 1, 2, 3
),
pk AS (
  SELECT DISTINCT ON (apt_seq, area_group) apt_seq, area_group, v AS peak, m AS peak_m
  FROM ref WHERE m < DATE '2022-07-01' ORDER BY apt_seq, area_group, v DESC, m
),
tr AS (
  SELECT DISTINCT ON (apt_seq, area_group) apt_seq, area_group, v AS trough, m AS trough_m
  FROM ref WHERE m >= DATE '2022-07-01' ORDER BY apt_seq, area_group, v, m
),
js AS (  -- 당월·전월 전세 (rent_monthly 는 월별 중앙값이라 건수 가중 평균으로 근사)
  SELECT apt_seq, area_group,
    sum(n_jeonse_new * jeonse_new_median_10k)::numeric / nullif(sum(n_jeonse_new) FILTER (WHERE jeonse_new_median_10k IS NOT NULL), 0) AS jnew,
    sum(n_jeonse_new) FILTER (WHERE jeonse_new_median_10k IS NOT NULL) AS nnew,
    sum(n_jeonse * jeonse_median_10k)::numeric / nullif(sum(n_jeonse) FILTER (WHERE jeonse_median_10k IS NOT NULL), 0) AS jall,
    sum(n_jeonse) FILTER (WHERE jeonse_median_10k IS NOT NULL) AS nall
  FROM rent_monthly WHERE contract_month IN ({CUR_M}, {PREV_M}) GROUP BY 1, 2
),
c AS (
  SELECT a1.*, hi.high_10k, hi.high_date, pk.peak, pk.peak_m, tr.trough, tr.trough_m, js.jnew, js.nnew, js.jall, js.nall,
    CASE WHEN n60 >= 3 THEN m60 WHEN n90 >= 3 THEN m90 WHEN n180 >= 3 THEN m180 END AS cur,
    CASE WHEN n60 >= 3 THEN n60 WHEN n90 >= 3 THEN n90 WHEN n180 >= 3 THEN n180 END AS cur_n,
    CASE WHEN n60 >= 3 THEN 60 WHEN n90 >= 3 THEN 90 WHEN n180 >= 3 THEN 180 END AS cur_days
  FROM a1 JOIN hi USING (apt_seq, area_group)
  LEFT JOIN pk USING (apt_seq, area_group) LEFT JOIN tr USING (apt_seq, area_group) LEFT JOIN js USING (apt_seq, area_group)
),
ph_months AS (  -- B1: 지난달까지 13개월 (월별 기준 시세 13개 = 변화 12개)
  SELECT generate_series(date_trunc('month', {TODAY}::date) - INTERVAL '13 month',
                         date_trunc('month', {TODAY}::date) - INTERVAL '1 month', INTERVAL '1 month')::date AS m
),
ref13 AS (
  SELECT b.apt_seq, b.area_group, mo.m, percentile_cont(0.5) WITHIN GROUP (ORDER BY b.price_10k) AS v
  FROM ph_months mo JOIN base b ON b.contract_date >= mo.m - INTERVAL '2 month' AND b.contract_date < mo.m + INTERVAL '1 month'
  GROUP BY 1, 2, 3
),
dv AS (
  SELECT apt_seq, area_group, m, v,
    v - lag(v) OVER (PARTITION BY apt_seq, area_group ORDER BY m) AS dv,
    row_number() OVER (PARTITION BY apt_seq, area_group ORDER BY m DESC) AS rn,
    count(*) OVER (PARTITION BY apt_seq, area_group) AS cnt,
    first_value(v) OVER (PARTITION BY apt_seq, area_group ORDER BY m) AS v0
  FROM ref13
),
ph0 AS (  -- 13개월 모두 기준 시세가 있는 단지만 (🔧 3개월 창에 거래가 하나도 없는 달이 있으면 판정 안 함)
  SELECT apt_seq, area_group,
    (max(v) FILTER (WHERE rn = 1) / max(v0) - 1) * 100 AS chg,
    count(*) FILTER (WHERE dv > 0) AS up, count(*) FILTER (WHERE dv < 0) AS down,
    bool_and(dv > 0) FILTER (WHERE rn <= 3) AS l3up, bool_and(dv < 0) FILTER (WHERE rn <= 3) AS l3dn
  FROM dv WHERE cnt = 13 GROUP BY 1, 2
),
ph AS (  -- collector/market.py phase() 와 같은 규칙: 🔧 ±3%, 8개월 / 📖 추세 최소 1년 p.136
  SELECT apt_seq, area_group, chg, up, down,
    CASE WHEN l3up THEN '상승' WHEN l3dn THEN '하락' ELSE '혼조' END AS last3,
    CASE WHEN chg >= 3 AND up >= 8 THEN '상승장' WHEN chg <= -3 AND down >= 8 THEN '하락장'
         WHEN abs(chg) < 3 THEN '보합장' WHEN l3up THEN '일시 반등' WHEN l3dn THEN '일시 조정' ELSE '추세 불명확' END AS phase
  FROM ph0
),
d AS (
  SELECT c.*, ph.phase, ph.chg, ph.up, ph.down, ph.last3, round(cur)::int AS ref,
    CASE WHEN cur IS NOT NULL AND peak IS NOT NULL AND trough IS NOT NULL AND peak > trough THEN (cur - trough) / (peak - trough) END AS rec,
    round(coalesce(jnew, jall))::int AS j, CASE WHEN jnew IS NOT NULL THEN nnew ELSE nall END AS jn,
    CASE WHEN jnew IS NOT NULL THEN '신규' WHEN jall IS NOT NULL THEN '전체' END AS jsrc
  FROM c LEFT JOIN ph USING (apt_seq, area_group)
)
SELECT apt_seq, area_group, {TODAY},
  ref, cur_n, cur_days,
  CASE cur_days WHEN 60 THEN '높음' WHEN 90 THEN '보통' WHEN 180 THEN '낮음' END,
  round(peak)::int, to_char(peak_m, 'YYYYMM'), round(trough)::int, to_char(trough_m, 'YYYYMM'),
  round(rec::numeric, 3),
  CASE WHEN ref IS NULL OR peak IS NULL THEN NULL
       WHEN ref >= peak THEN '신고가 돌파'
       WHEN rec >= 0.6 AND (phase IS NULL OR phase IN ('상승장', '보합장')) THEN '순조로운 회복'   -- 🔧 60%, B1 상승장·보합장 (국면 판정 불가 단지는 회복률만)
       ELSE '회복 지연' END,
  CASE WHEN ref IS NOT NULL AND trough IS NOT NULL THEN ref <= trough * 1.03 END,
  j, jn, jsrc,
  CASE WHEN j IS NOT NULL AND ref IS NOT NULL THEN round(j * 100.0 / ref, 1) END,
  CASE WHEN ref IS NULL THEN NULL WHEN ref <= 50000 THEN 60 WHEN ref <= 80000 THEN 60 - 10 * (ref - 50000) / 30000.0
       WHEN ref <= 150000 THEN 50 WHEN ref <= 200000 THEN 50 - 20 * (ref - 150000) / 50000.0 ELSE 30 END,
  CASE WHEN ref IS NULL THEN NULL WHEN ref <= 50000 THEN 90 WHEN ref <= 80000 THEN 90 - 30 * (ref - 50000) / 30000.0
       WHEN ref <= 150000 THEN 60 WHEN ref <= 200000 THEN 60 - 10 * (ref - 150000) / 50000.0 ELSE 50 END,
  n_365, high_10k, high_date, last_date,
  phase, round(chg::numeric, 2), up, down, last3
FROM d;

COMMIT;
