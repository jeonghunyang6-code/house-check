-- 단지 지표 계산 (jobs/metrics.py 가 {TODAY}·{PREV_DAYS}·{CUR_M}·{PREV_M} 를 채워 실행한다). 0010_metrics.sql 참고.
BEGIN;

-- 1) 최근 계약 거래의 전고점 (ARCHITECTURE 4.3: 이전 계약일의 중개·비해제 최고가)
--    DB 밖으로 보관한 과거 거래의 최고가(deal_anchor)와 합친다 (저장 구조 C, GREATEST 는 NULL 을 무시)
--    최근 🔧 14일 안에 해제가 확인된 단지·면적군은 기간과 상관없이 모두 다시 계산한다(해제된 거래가 전고점으로 남지 않게,
--    jobs/daily.py recheck_month 가 지난 1년 달을 돌아가며 다시 받는다)
UPDATE deals d SET prev_high_10k = GREATEST((
  SELECT max(p.price_10k) FROM deals p
  WHERE p.apt_seq = d.apt_seq AND p.area_group = d.area_group AND p.contract_date < d.contract_date
    AND NOT p.is_cancelled AND p.deal_type = '중개'),
  (SELECT a.hist_high_10k FROM deal_anchor a WHERE a.apt_seq = d.apt_seq AND a.area_group = d.area_group))
WHERE d.contract_date >= {TODAY} - {PREV_DAYS}
   OR (d.apt_seq, d.area_group) IN (
     SELECT x.apt_seq, x.area_group FROM deal_events e JOIN deals x USING (deal_key)
     WHERE e.event = 'cancelled' AND e.event_date >= {TODAY} - 14);

-- 2) 단지 × 면적군 지표
DELETE FROM complex_metrics;
INSERT INTO complex_metrics
WITH base AS (  -- 기준 시세용: 중개·비해제, 1층 제외 (📖 P1 "1층 제외, 중층 이상" 영상 1:33. 2026-10-18 실측 1층 약 8% 낮음)
  SELECT apt_seq, area_group, contract_date, price_10k FROM deals
  WHERE NOT is_cancelled AND deal_type = '중개' AND floor IS DISTINCT FROM 1
),
a1 AS (
  SELECT apt_seq, area_group,
    count(*) FILTER (WHERE contract_date > {TODAY} - 60)  AS n60,
    count(*) FILTER (WHERE contract_date > {TODAY} - 90)  AS n90,
    count(*) FILTER (WHERE contract_date > {TODAY} - 180) AS n180,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 60)  AS m60,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 90)  AS m90,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE contract_date > {TODAY} - 180) AS m180,
    max(n_365) AS n_365, max(last_date) AS last_date
  FROM base RIGHT JOIN (  -- 거래 수·마지막 거래일은 1층 포함
    SELECT apt_seq, area_group, count(*) FILTER (WHERE contract_date > {TODAY} - 365) AS n_365, max(contract_date) AS last_date
    FROM deals WHERE NOT is_cancelled AND deal_type = '중개' GROUP BY 1, 2) al USING (apt_seq, area_group)
  GROUP BY 1, 2
),
hi AS (  -- 역대 최고 = DB 구간 + 보관 구간(deal_anchor)
  SELECT DISTINCT ON (apt_seq, area_group) apt_seq, area_group, high_10k, high_date FROM (
    SELECT apt_seq, area_group, price_10k AS high_10k, contract_date AS high_date FROM deals WHERE NOT is_cancelled AND deal_type = '중개'
    UNION ALL SELECT apt_seq, area_group, hist_high_10k, hist_high_date FROM deal_anchor) x
  ORDER BY apt_seq, area_group, high_10k DESC, high_date
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
js AS (  -- 당월·전월 전세: DB 원본(rents)의 실제 중앙값. 신규가 있으면 신규, 없으면 전체(갱신·유형 공백 포함). 사라진 신고 제외
  SELECT apt_seq, area_group,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY deposit_10k) FILTER (WHERE contract_type = '신규') AS jnew,
    count(*) FILTER (WHERE contract_type = '신규') AS nnew,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY deposit_10k) AS jall, count(*) AS nall
  FROM rents WHERE contract_month IN ({CUR_M}, {PREV_M}) AND monthly_rent_10k = 0 AND NOT disappeared
  GROUP BY 1, 2
),
c AS (
  -- B2 고점·저점: 보관 파일에서 계산한 값(deal_anchor)이 있으면 그것, 없으면 DB 의 거래로 계산한 값
  SELECT a1.*, hi.high_10k, hi.high_date, coalesce(an.peak_10k, pk.peak) AS peak, coalesce(an.peak_m, to_char(pk.peak_m, 'YYYYMM')) AS peak_m,
    coalesce(an.trough_10k, tr.trough) AS trough, coalesce(an.trough_m, to_char(tr.trough_m, 'YYYYMM')) AS trough_m, an.p20_10k,
    js.jnew, js.nnew, js.jall, js.nall,
    CASE WHEN n60 >= 3 THEN m60 WHEN n90 >= 3 THEN m90 WHEN n180 >= 3 THEN m180 END AS cur,
    CASE WHEN n60 >= 3 THEN n60 WHEN n90 >= 3 THEN n90 WHEN n180 >= 3 THEN n180 END AS cur_n,
    CASE WHEN n60 >= 3 THEN 60 WHEN n90 >= 3 THEN 90 WHEN n180 >= 3 THEN 180 END AS cur_days
  FROM a1 JOIN hi USING (apt_seq, area_group)
  LEFT JOIN pk USING (apt_seq, area_group) LEFT JOIN tr USING (apt_seq, area_group) LEFT JOIN js USING (apt_seq, area_group)
  LEFT JOIN deal_anchor an USING (apt_seq, area_group)
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
rs AS (  -- B6 상대강도 (📖 상승의 차이 p.420~421): 같은 시군구 판정 단지들의 12개월 변화 중앙값 (생활권에 판정 단지가 적을 때 대신 쓴다)
  SELECT x.region_code, percentile_cont(0.5) WITHIN GROUP (ORDER BY ph.chg) AS region_chg, count(*) AS region_n
  FROM ph JOIN (SELECT DISTINCT apt_seq, region_code FROM deals) x USING (apt_seq) GROUP BY 1
),
rz AS (  -- B6: 같은 생활권(E0, jobs/lifezone.py) 판정 단지들의 12개월 변화 중앙값
  SELECT x.lifezone_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY ph.chg) AS zone_chg, count(*) AS zone_n
  FROM ph JOIN complexes x USING (apt_seq) WHERE x.lifezone_id IS NOT NULL GROUP BY 1
),
j24 AS (  -- D3: 24개월 전 ±1개월 전세 계약(신규·갱신). rent_j24(보관 파일 원본의 실제 중앙값, jobs/rent_archive.py)를 먼저 쓰고,
          --     그 창의 값이 없으면 월별 중앙값(rent_monthly)의 건수 가중 평균으로 근사
  SELECT apt_seq, area_group, coalesce(t.median_10k, a.j24) AS j24, CASE WHEN t.n IS NOT NULL THEN t.n ELSE a.n24 END AS n24
  FROM (
    SELECT apt_seq, area_group,
      sum(n_jeonse * jeonse_median_10k)::numeric / nullif(sum(n_jeonse) FILTER (WHERE jeonse_median_10k IS NOT NULL), 0) AS j24,
      sum(n_jeonse) FILTER (WHERE jeonse_median_10k IS NOT NULL) AS n24
    FROM rent_monthly
    WHERE contract_month BETWEEN to_char({TODAY}::date - INTERVAL '25 months', 'YYYYMM') AND to_char({TODAY}::date - INTERVAL '23 months', 'YYYYMM')
    GROUP BY 1, 2) a
  FULL JOIN (SELECT apt_seq, area_group, n, median_10k FROM rent_j24
             WHERE from_month = to_char({TODAY}::date - INTERVAL '25 months', 'YYYYMM')) t USING (apt_seq, area_group)
),
b20 AS (  -- A6: 2020년 1분기 중개 거래 중앙값 (수집 시작 시점)
  SELECT apt_seq, area_group, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) AS p20
  FROM base WHERE contract_date >= DATE '2020-01-01' AND contract_date < DATE '2020-04-01' GROUP BY 1, 2
),
cpi AS (
  SELECT (SELECT value FROM macro_monthly WHERE series = 'cpi' ORDER BY period DESC LIMIT 1) AS now_,
         (SELECT avg(value) FROM macro_monthly WHERE series = 'cpi' AND period BETWEEN '202001' AND '202003') AS q120
),
d AS (
  SELECT c.*, ph.phase, j24.j24, j24.n24, coalesce(c.p20_10k, b20.p20) AS p20, cpi.now_ AS cpi_now, cpi.q120 AS cpi_20, ph.chg, ph.up, ph.down, ph.last3,
    -- 🔧 판정 단지 5개 이상인 생활권, 없으면 같은 조건의 시군구
    CASE WHEN ph.chg IS NULL THEN NULL WHEN rz.zone_n >= 5 THEN rz.zone_chg WHEN rs.region_n >= 5 THEN rs.region_chg END AS region_chg,
    round(cur)::int AS ref,
    CASE WHEN cur IS NOT NULL AND peak IS NOT NULL AND trough IS NOT NULL AND peak > trough THEN (cur - trough) / (peak - trough) END AS rec,
    round(coalesce(jnew, jall))::int AS j, CASE WHEN jnew IS NOT NULL THEN nnew ELSE nall END AS jn,
    CASE WHEN jnew IS NOT NULL THEN '신규' WHEN jall IS NOT NULL THEN '전체' END AS jsrc
  FROM c LEFT JOIN ph USING (apt_seq, area_group)
  LEFT JOIN (SELECT DISTINCT ON (apt_seq) apt_seq, region_code FROM deals ORDER BY apt_seq, contract_date DESC) rc USING (apt_seq)
  LEFT JOIN rs ON rs.region_code = rc.region_code
  LEFT JOIN complexes cz USING (apt_seq) LEFT JOIN rz ON rz.lifezone_id = cz.lifezone_id
  LEFT JOIN j24 USING (apt_seq, area_group) LEFT JOIN b20 USING (apt_seq, area_group) CROSS JOIN cpi
)
SELECT apt_seq, area_group, {TODAY},
  ref, cur_n, cur_days,
  CASE cur_days WHEN 60 THEN '높음' WHEN 90 THEN '보통' WHEN 180 THEN '낮음' END,
  round(peak)::int, peak_m, round(trough)::int, trough_m,
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
  phase, round(chg::numeric, 2), up, down, last3,
  round(region_chg::numeric, 2), round((chg - region_chg)::numeric, 2),
  -- D3 (📖 p.153): 24개월 전 전세 2건 이상일 때만 판정
  CASE WHEN n24 >= 2 THEN round(j24)::int END, n24,
  CASE WHEN j IS NOT NULL AND n24 >= 2 THEN j < j24 END,
  CASE WHEN j IS NOT NULL THEN round(j * 0.1)::int END,
  -- A6: 2020=100 원화 기준 실질 시세, 2020년 1분기 대비 실질 변화
  CASE WHEN ref IS NOT NULL AND cpi_now > 0 THEN round(ref * 100.0 / cpi_now)::int END,
  round(p20)::int,
  CASE WHEN ref IS NOT NULL AND p20 > 0 AND cpi_now > 0 AND cpi_20 > 0 THEN round((((ref / cpi_now) / (p20 / cpi_20) - 1) * 100)::numeric, 1) END
FROM d;

-- 2-1) A1 자료 충분도 근거: 기준 시세 창 안 거래(1층 제외)의 가격 범위, 뺀 1층 건수
UPDATE complex_metrics m SET ref_lo_10k = x.lo, ref_hi_10k = x.hi, ref_floor1_n = x.f1
FROM (
  SELECT d.apt_seq, d.area_group,
    min(d.price_10k) FILTER (WHERE d.floor IS DISTINCT FROM 1) AS lo, max(d.price_10k) FILTER (WHERE d.floor IS DISTINCT FROM 1) AS hi,
    count(*) FILTER (WHERE d.floor = 1) AS f1
  FROM deals d JOIN complex_metrics c USING (apt_seq, area_group)
  WHERE c.ref_days IS NOT NULL AND NOT d.is_cancelled AND d.deal_type = '중개' AND d.contract_date > {TODAY} - c.ref_days
  GROUP BY 1, 2) x
WHERE m.apt_seq = x.apt_seq AND m.area_group = x.area_group;

UPDATE complex_metrics m SET jeonse_24m_approx = NOT EXISTS (
  SELECT 1 FROM rent_j24 t WHERE t.apt_seq = m.apt_seq AND t.area_group = m.area_group
    AND t.from_month = to_char({TODAY}::date - INTERVAL '25 months', 'YYYYMM'))
WHERE jeonse_24m_10k IS NOT NULL;

-- 3) C2 월 거래 회전율 (📖 0.5~0.8% = 꽤 괜찮은 거래량 p.137): 단지 단위라 모든 면적군에 같은 값.
--    집계 끝난 달 = 지지난 달까지(신고 기한 30일), 최근 12개월 평균. 세대수는 K-apt (0008)
WITH tv AS (
  SELECT d.apt_seq, count(*) / 12.0 AS per_month FROM deals d
  WHERE NOT d.is_cancelled
    AND d.contract_month BETWEEN to_char(date_trunc('month', {TODAY}::date) - INTERVAL '13 month', 'YYYYMM')
                             AND to_char(date_trunc('month', {TODAY}::date) - INTERVAL '2 month', 'YYYYMM')
  GROUP BY 1
), hh AS (
  SELECT c.apt_seq, k.households FROM complexes c JOIN kapt_complexes k ON k.kapt_code = c.kapt_code WHERE k.households > 0
)
UPDATE complex_metrics m SET households = hh.households,
  turnover_pct = round((coalesce(tv.per_month, 0) * 100.0 / hh.households)::numeric, 2),
  turnover_state = CASE WHEN coalesce(tv.per_month, 0) * 100.0 / hh.households < 0.5 THEN '적음'
                        WHEN coalesce(tv.per_month, 0) * 100.0 / hh.households <= 0.8 THEN '꽤 괜찮음' ELSE '많음' END
FROM hh LEFT JOIN tv USING (apt_seq) WHERE m.apt_seq = hh.apt_seq;

-- 4) E3 바로 위 급지 비교 단지 (📖 미래 시세 = 바로 위 급지 현재 시세 p.358~359, 과도한 비교 금지 p.362) + B6 위 급지 대비 상대강도.
--    명세: 같은 생활권 또는 인접 생활권에서 ㎡당 기준 시세가 🔧 10~40% 높은 단지 중 가장 가까운 3곳.
--    → 같은 생활권(E0) 또는 🔧 직선 5km 안·한강 같은 쪽, 같은 생활권 먼저·가까운 순. 좌표 없는 단지는 같은 시군구.
--    (3km 로는 작가 사다리 고덕 → 올림픽파크포레온(약 5km)이 빠져 5km. 띠는 ±2(약 7km))
--    면적군 차이 15㎡ 이내(비슷한 평형끼리). 위도 띠(약 3.7km)로 나눠 가까운 띠끼리만 비교한다(속도)
WITH b AS (
  SELECT m.apt_seq, m.area_group, m.ref_10k::numeric / m.area_group AS ppm, m.chg_12m, x.region_code,
    x.lifezone_id AS z, x.lat, x.lng, ad.han_side AS side, floor(x.lat * 30)::int AS band
  FROM complex_metrics m JOIN complexes x USING (apt_seq) LEFT JOIN adm_dong ad ON ad.adm_cd = x.adm_cd
  WHERE m.ref_10k IS NOT NULL AND m.area_group BETWEEN 40 AND 135
), pc AS (
  SELECT a.apt_seq, a.area_group, o.apt_seq AS o_seq, o.ppm, o.chg_12m, a.z = o.z AS same_z,
    111320 * sqrt(power(o.lat - a.lat, 2) + power((o.lng - a.lng) * 0.7934, 2)) AS dist,
    coalesce(o.side, '') = coalesce(a.side, '') AS same_side
  FROM b a CROSS JOIN generate_series(-2, 2) g(k) JOIN b o ON o.band = a.band + g.k
  WHERE a.lat IS NOT NULL AND o.apt_seq <> a.apt_seq
    AND o.ppm BETWEEN a.ppm * 1.1 AND a.ppm * 1.4 AND abs(o.area_group - a.area_group) <= 15
  UNION ALL
  SELECT a.apt_seq, a.area_group, o.apt_seq, o.ppm, o.chg_12m, false, NULL, true
  FROM b a JOIN b o ON o.region_code = a.region_code AND o.apt_seq <> a.apt_seq
  WHERE a.lat IS NULL AND o.ppm BETWEEN a.ppm * 1.1 AND a.ppm * 1.4 AND abs(o.area_group - a.area_group) <= 15
), p AS (
  SELECT pc.*, row_number() OVER (PARTITION BY apt_seq, area_group ORDER BY same_z DESC NULLS LAST, dist NULLS LAST, ppm, o_seq) AS rn
  FROM pc WHERE dist IS NULL OR same_z OR (dist <= 5000 AND same_side)
), e AS (
  SELECT apt_seq, area_group, percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm) AS e_ppm,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY chg_12m) AS e_chg, string_agg(DISTINCT o_seq, ',') AS seqs
  FROM p WHERE rn <= 3 GROUP BY 1, 2
)
UPDATE complex_metrics m SET e3_seqs = e.seqs, e3_target_10k = round(e.e_ppm * m.area_group)::int,
  e3_chg_12m = round(e.e_chg::numeric, 2), rel_strength_e3 = round((m.chg_12m - e.e_chg)::numeric, 2)
FROM e WHERE m.apt_seq = e.apt_seq AND m.area_group = e.area_group;

-- 5) E2 주변 시세 위치 (📖 주변 시세가 높은 곳이 상승 여력이 크다 p.216~217, p.339, p.342; 명세: 같은 생활권, 없으면 반경 1.5km).
--    이 단지 ㎡당 기준 시세 ÷ 주변 다른 단지(면적군 ±15㎡) ㎡당 기준 시세 중앙값. 🔧 주변 단지 3곳 이상일 때만.
--    같은 생활권에 3곳이 안 되면 직선 1.5km 안·한강 같은 쪽 단지로
WITH b AS (
  SELECT m.apt_seq, m.area_group, m.ref_10k::numeric / m.area_group AS ppm, x.lifezone_id AS z, x.lat, x.lng,
    ad.han_side AS side, floor(x.lat * 30)::int AS band
  FROM complex_metrics m JOIN complexes x USING (apt_seq) LEFT JOIN adm_dong ad ON ad.adm_cd = x.adm_cd
  WHERE m.ref_10k IS NOT NULL AND m.area_group BETWEEN 40 AND 135
), pz AS (
  SELECT a.apt_seq, a.area_group, percentile_cont(0.5) WITHIN GROUP (ORDER BY o.ppm) AS med, count(DISTINCT o.apt_seq) AS n
  FROM b a JOIN b o ON o.z = a.z AND o.apt_seq <> a.apt_seq AND abs(o.area_group - a.area_group) <= 15
  GROUP BY 1, 2
), pr AS (
  SELECT a.apt_seq, a.area_group, percentile_cont(0.5) WITHIN GROUP (ORDER BY o.ppm) AS med, count(DISTINCT o.apt_seq) AS n
  FROM b a CROSS JOIN generate_series(-1, 1) g(k) JOIN b o ON o.band = a.band + g.k
  WHERE a.lat IS NOT NULL AND o.apt_seq <> a.apt_seq AND abs(o.area_group - a.area_group) <= 15
    AND coalesce(o.side, '') = coalesce(a.side, '')
    AND 111320 * sqrt(power(o.lat - a.lat, 2) + power((o.lng - a.lng) * 0.7934, 2)) <= 1500
  GROUP BY 1, 2
), e AS (
  SELECT b.apt_seq, b.area_group,
    CASE WHEN pz.n >= 3 THEN b.ppm / pz.med WHEN pr.n >= 3 THEN b.ppm / pr.med END AS ratio,
    CASE WHEN pz.n >= 3 THEN pz.n WHEN pr.n >= 3 THEN pr.n END AS n,
    CASE WHEN pz.n >= 3 THEN '생활권' WHEN pr.n >= 3 THEN '반경 1.5km' END AS basis
  FROM b LEFT JOIN pz USING (apt_seq, area_group) LEFT JOIN pr USING (apt_seq, area_group)
)
UPDATE complex_metrics m SET e2_ratio = round(e.ratio::numeric, 3), e2_n = e.n, e2_basis = e.basis
FROM e WHERE m.apt_seq = e.apt_seq AND m.area_group = e.area_group AND e.ratio IS NOT NULL;

-- 6) E4 한계 시세 (📖 하급지 84㎡ 천장 = 상급지 59㎡ 가격, 상급지가 오르면 천장도 오른다 p.217~219, p.228).
--    ① 84㎡(면적군 80~89) 행: E3 비교 단지들의 59㎡(55~64) 기준 시세 중앙값 = 천장. 2026-10-16 전체로 보면 84 ÷ 천장 중앙값 0.99
--    ② 단지 안 평형 압축 (📖 예: 24평 11억 / 32평 13억 / 42평 14억 p.231): 최근 1년 중개 거래로 59(55~64)·84(80~89)·대형(100~135)
--       각 🔧 2건 이상일 때 (대형-84 ㎡당 추가 가격) ÷ (84-59 ㎡당 추가 가격). 작을수록 큰 평형 값이 덜 붙음. 작가 예는 약 0.5,
--       경계 숫자는 없어 🔧 기준선 없이 값만 (2026-10-16 중앙값 약 0.6이라 예시 수준이 흔하다)
WITH c AS (
  SELECT a.apt_seq, a.area_group, percentile_cont(0.5) WITHIN GROUP (ORDER BY o.ref_10k) AS cap, count(DISTINCT o.apt_seq) AS n
  FROM complex_metrics a JOIN complex_metrics o ON o.apt_seq = ANY(string_to_array(a.e3_seqs, ','))
    AND o.area_group BETWEEN 55 AND 64 AND o.ref_10k IS NOT NULL
  WHERE a.area_group BETWEEN 80 AND 89 AND a.e3_seqs IS NOT NULL
  GROUP BY 1, 2
)
UPDATE complex_metrics m SET e4_cap_10k = round(c.cap)::int, e4_cap_n = c.n
FROM c WHERE m.apt_seq = c.apt_seq AND m.area_group = c.area_group;

WITH d AS (
  SELECT apt_seq, CASE WHEN area_m2 >= 55 AND area_m2 < 65 THEN 's' WHEN area_m2 >= 80 AND area_m2 < 90 THEN 'm'
    WHEN area_m2 >= 100 AND area_m2 <= 135 THEN 'l' END AS k, area_m2, price_10k
  FROM deals WHERE NOT is_cancelled AND deal_type = '중개' AND floor IS DISTINCT FROM 1 AND contract_date > {TODAY} - 365
), g AS (
  SELECT apt_seq,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE k = 's') AS ps, percentile_cont(0.5) WITHIN GROUP (ORDER BY area_m2) FILTER (WHERE k = 's') AS as_,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE k = 'm') AS pm, percentile_cont(0.5) WITHIN GROUP (ORDER BY area_m2) FILTER (WHERE k = 'm') AS am,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE k = 'l') AS pl, percentile_cont(0.5) WITHIN GROUP (ORDER BY area_m2) FILTER (WHERE k = 'l') AS al
  FROM d WHERE k IS NOT NULL GROUP BY 1
  HAVING count(*) FILTER (WHERE k = 's') >= 2 AND count(*) FILTER (WHERE k = 'm') >= 2 AND count(*) FILTER (WHERE k = 'l') >= 2
), e AS (
  SELECT apt_seq, ((pl - pm) / (al - am)) / ((pm - ps) / (am - as_)) AS k,
    format('%s㎡ %s억 / %s㎡ %s억 / %s㎡ %s억', floor(as_), round((ps / 1e4)::numeric, 1), floor(am), round((pm / 1e4)::numeric, 1),
      floor(al), round((pl / 1e4)::numeric, 1)) AS sizes
  FROM g WHERE pm > ps AND am > as_ AND al > am
)
UPDATE complex_metrics m SET e4_compress = round(greatest(least(e.k, 99), -99)::numeric, 3), e4_sizes = e.sizes
FROM e WHERE m.apt_seq = e.apt_seq;

-- 7) E5·E7 생활권 단위 (lifezone 표). 최근 1년 중개 거래, 단지별 ㎡당 중앙가.
--    E5 (📖 대형 평형 평당가는 눌린다, 비싼 지역일수록 소형·대형 평당가가 비슷 p.247~250, p.468):
--       단지별 (전용 100~135 ㎡당) ÷ (75~100 ㎡당), 각 🔧 2건 이상. 생활권 중앙값, 🔧 단지 3곳 이상
--    E7 (📖 신축 5천 → 준신축 4천 → 구축 3천 p.56, 2016년 이후 표준 p.467): 준공 5년 이내 / 6~15년 / 16년+,
--       전용 40~135, 단지 🔧 2건 이상. 구간별 단지 중앙가의 중앙값, 🔧 구간에 단지 2곳 이상일 때만
UPDATE lifezone SET e5_ratio = NULL, e5_n = NULL, e7_new_ppm = NULL, e7_mid_ppm = NULL, e7_old_ppm = NULL, e7_n = NULL;

WITH d AS (
  SELECT d.apt_seq, x.lifezone_id AS z, d.area_m2, d.price_10k / d.area_m2 AS ppm
  FROM deals d JOIN complexes x USING (apt_seq)
  WHERE NOT d.is_cancelled AND d.deal_type = '중개' AND d.floor IS DISTINCT FROM 1 AND d.contract_date > {TODAY} - 365 AND x.lifezone_id IS NOT NULL
), c AS (
  SELECT apt_seq, z,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm) FILTER (WHERE area_m2 >= 75 AND area_m2 < 100) AS p30,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm) FILTER (WHERE area_m2 >= 100 AND area_m2 <= 135) AS p40
  FROM d GROUP BY 1, 2
  HAVING count(*) FILTER (WHERE area_m2 >= 75 AND area_m2 < 100) >= 2 AND count(*) FILTER (WHERE area_m2 >= 100 AND area_m2 <= 135) >= 2
), e AS (
  SELECT z, percentile_cont(0.5) WITHIN GROUP (ORDER BY p40 / p30) AS r, count(*) AS n FROM c GROUP BY 1 HAVING count(*) >= 3
)
UPDATE lifezone l SET e5_ratio = round(e.r::numeric, 3), e5_n = e.n FROM e WHERE l.zone_id = e.z;

WITH d AS (
  SELECT d.apt_seq, x.lifezone_id AS z, x.build_year, d.price_10k / d.area_m2 AS ppm
  FROM deals d JOIN complexes x USING (apt_seq)
  WHERE NOT d.is_cancelled AND d.deal_type = '중개' AND d.floor IS DISTINCT FROM 1 AND d.area_m2 BETWEEN 40 AND 135 AND d.contract_date > {TODAY} - 365
    AND x.lifezone_id IS NOT NULL AND x.build_year IS NOT NULL
), c AS (
  SELECT apt_seq, z, CASE WHEN extract(year FROM {TODAY}) - max(build_year) <= 5 THEN 'new'
    WHEN extract(year FROM {TODAY}) - max(build_year) <= 15 THEN 'mid' ELSE 'old' END AS k,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm) AS p
  FROM d GROUP BY 1, 2 HAVING count(*) >= 2
), e AS (
  SELECT z, count(*) FILTER (WHERE k = 'new') AS nn, count(*) FILTER (WHERE k = 'mid') AS nm, count(*) FILTER (WHERE k = 'old') AS no,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY p) FILTER (WHERE k = 'new') AS pn,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY p) FILTER (WHERE k = 'mid') AS pm,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY p) FILTER (WHERE k = 'old') AS po
  FROM c GROUP BY 1
)
UPDATE lifezone l SET e7_new_ppm = CASE WHEN e.nn >= 2 THEN round(e.pn::numeric, 1) END,
  e7_mid_ppm = CASE WHEN e.nm >= 2 THEN round(e.pm::numeric, 1) END, e7_old_ppm = CASE WHEN e.no >= 2 THEN round(e.po::numeric, 1) END,
  e7_n = e.nn || '/' || e.nm || '/' || e.no
FROM e WHERE l.zone_id = e.z;

-- 8) F1 입주 물량 (📖 입주 시작 후 5~6개월이 입주장 p.55, 입주 물량이 전세를 누른다 p.154, p.423). presale(0034·0035): 총 세대
--    (K-apt, 입주 전 정비사업은 추정, 아니면 청약홈 공급 세대). 한국부동산원 입주 예정 물량(0037)이 다루는 달은 그 실제 총 세대로. 같은 생활권·같은 시군구에서 이번 달부터 24개월 안 입주 세대 합.
--    입주장 = 같은 생활권에서 입주 예정월이 최근 6개월(이번 달 포함) 안인 단지
WITH cx AS (SELECT DISTINCT m.apt_seq, x.lifezone_id AS z, x.region_code AS rc FROM complex_metrics m JOIN complexes x USING (apt_seq)),
cur AS (SELECT to_char({TODAY}, 'YYYYMM') AS c, to_char({TODAY} + INTERVAL '23 month', 'YYYYMM') AS e,
               to_char({TODAY} - INTERVAL '5 month', 'YYYYMM') AS s),
pr AS (SELECT min(move_in_ym) AS a, max(move_in_ym) AS b FROM ipju_plan),
p AS (   -- 입주 월마다 출처 하나: 한국부동산원 입주 예정 물량(ipju_plan)이 다루는 달은 그 표만, 나머지 달은 청약홈(presale 총 세대)
  SELECT name, move_in_ym, households AS hh, lifezone_id, region_code FROM ipju_plan
  UNION ALL
  SELECT q.name, q.move_in_ym, coalesce(q.total_hh, q.households), q.lifezone_id, q.region_code FROM presale q, pr
  WHERE pr.a IS NULL OR q.move_in_ym < pr.a OR q.move_in_ym > pr.b),
z AS (SELECT p.lifezone_id AS z, sum(p.hh) AS hh FROM p, cur WHERE p.move_in_ym BETWEEN cur.c AND cur.e GROUP BY 1),
g AS (SELECT p.region_code AS rc, sum(p.hh) AS hh FROM p, cur WHERE p.move_in_ym BETWEEN cur.c AND cur.e GROUP BY 1),
ip AS (SELECT p.lifezone_id AS z, string_agg(format('%s(%s.%s, %s세대)', p.name, left(p.move_in_ym, 4), right(p.move_in_ym, 2), p.hh),
         ', ' ORDER BY p.move_in_ym DESC, p.hh DESC) AS t
       FROM p, cur WHERE p.move_in_ym BETWEEN cur.s AND cur.c AND p.lifezone_id IS NOT NULL GROUP BY 1),
nx AS (SELECT DISTINCT ON (p.lifezone_id) p.lifezone_id AS z,
         format('%s(%s.%s, %s세대)', p.name, left(p.move_in_ym, 4), right(p.move_in_ym, 2), p.hh) AS t
       FROM p, cur WHERE p.move_in_ym > cur.c AND p.move_in_ym <= cur.e AND p.lifezone_id IS NOT NULL
       ORDER BY p.lifezone_id, p.hh DESC, p.move_in_ym),
v AS (SELECT cx.apt_seq, coalesce(z.hh, 0) AS zh, coalesce(g.hh, 0) AS gh, ip.t AS ip, nx.t AS nx, cx.z
      FROM cx LEFT JOIN z ON z.z = cx.z LEFT JOIN g ON g.rc = cx.rc LEFT JOIN ip ON ip.z = cx.z LEFT JOIN nx ON nx.z = cx.z)
UPDATE complex_metrics m SET f1_zone_24m = CASE WHEN v.z IS NOT NULL THEN v.zh END, f1_sgg_24m = v.gh, f1_ipju = v.ip, f1_next = v.nx
FROM v WHERE m.apt_seq = v.apt_seq;

COMMIT;
