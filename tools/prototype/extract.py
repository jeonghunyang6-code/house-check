"""시안용 원자료를 DB 에서 뽑는다 → tools/prototype/out/raw.json. 실행: python tools/prototype/extract.py"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'tools/prototype/out'; OUT.mkdir(exist_ok=True)
from collector.db import connect, select
from collector.regions import REGIONS
db = connect('api')
out = {}
# A. 서울 월별 거래량(해제 제외)과 84㎡ 중위 가격
#    DB 에 없는 옛 달(저장 구조 C: 2년 이전은 보관 파일)은 deal_region_month 의 서울 합계('11')로 채운다
out['monthly'] = select(db, """
 SELECT contract_month m, n_all - n_cancelled n, p84_median_10k p84 FROM deal_region_month
 WHERE region_code = '11' AND contract_month < (SELECT min(contract_month) FROM deals)
 UNION ALL
 SELECT contract_month m, count(*) FILTER (WHERE NOT is_cancelled) n,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE NOT is_cancelled AND deal_type='중개' AND area_group IN (84,85)) p84
 FROM deals WHERE region_code LIKE '11%' GROUP BY 1 ORDER BY 1""")
# A2. C1 신고 지연 보정 (volume_nowcast, jobs/volume.py) — 서울 최신
out['nowcast'] = select(db, """SELECT contract_month m, observed, share, est, lo, hi, est_full FROM volume_nowcast
 WHERE region_code = '11' AND asof = (SELECT max(asof) FROM volume_nowcast)""")
# B. 오늘 처음 등록된 거래 + 전고점 (직거래·해제 제외, 4.3)
#    전고점은 서버가 계산한 deals.prev_high_10k (DB 거래 + 보관 구간 최고가, sql/metrics.sql 1) 를 그대로 쓴다
PREV = "d.prev_high_10k"
out['today'] = select(db, f"""
 SELECT d.apt_name, d.apt_seq, d.region_code, d.contract_date::text cd, d.area_m2, d.area_group, d.floor, d.price_10k,
  d.deal_type, d.is_cancelled, {PREV} prev_high,
  (SELECT count(*) FROM deals p WHERE p.apt_seq=d.apt_seq AND p.area_group=d.area_group) hist_n
 FROM deals d WHERE d.first_seen_date = '2026-10-12' ORDER BY d.price_10k DESC""")
# C. 서울 최근 2개월 신고가
out['recent_highs'] = select(db, f"""
 SELECT * FROM (SELECT d.apt_name, d.region_code, d.contract_date::text cd, d.area_group, d.floor, d.price_10k, {PREV} prev_high
  FROM deals d WHERE d.region_code LIKE '11%' AND d.contract_month IN ('202609','202610')
  AND NOT d.is_cancelled AND d.deal_type='중개') t WHERE prev_high IS NOT NULL ORDER BY cd""")
# D. 비교 단지
SEQS = ['11710-8865','11680-218','11740-4628','11200-3120','11590-3954','11410-4479','11230-2587','11500-5419','11350-133']
sl = ",".join(f"'{s}'" for s in SEQS)
out['cx_deals'] = select(db, f"""SELECT apt_seq, apt_name, contract_date::text cd, area_group, floor, price_10k, deal_type, is_cancelled
 FROM deals WHERE apt_seq IN ({sl}) AND area_group IN (84,85) ORDER BY contract_date""")
# 저장 구조 C: DB 에 없는 옛 거래는 시군구별 과거 파일(deals_hist_<시군구>.csv.gz)에서. HC_ARCHIVE(기본 dir:data/archive)
import math
from collector.archive import decode, open_store
import os
_store = open_store(os.environ.get('HC_ARCHIVE') or f'dir:{ROOT}/data/archive')
_first = min((r['cd'] for r in out['cx_deals']), default='9999')
for _rc in sorted({s.split('-')[0] for s in SEQS}):
    _data = _store.get(f'deals_hist_{_rc}.csv.gz')
    if _data is None:
        print(f'  과거 파일 없음: deals_hist_{_rc}.csv.gz (단지 차트는 DB 구간만)')
        continue
    for r in decode(_data):
        ag = math.floor(float(r['area_m2']))
        if r['apt_seq'] in SEQS and ag in (84, 85) and r['contract_date'] < _first:
            out['cx_deals'].append(dict(apt_seq=r['apt_seq'], apt_name=r['apt_name'], cd=r['contract_date'], area_group=ag, floor=int(r['floor']),
                                        price_10k=int(r['price_10k']), deal_type=r['deal_type'], is_cancelled=r['is_cancelled'] in ('1', 'True', 'true')))
out['cx_deals'].sort(key=lambda r: r['cd'])
out['cx_rent'] = select(db, f"""SELECT apt_seq, contract_month m, area_group, n_jeonse, jeonse_median_10k, n_jeonse_new, jeonse_new_median_10k, n_jeonse_renew
 FROM rent_monthly WHERE apt_seq IN ({sl}) AND area_group IN (84,85) ORDER BY contract_month""")
# DB 에는 최근 17개월만(0053). 그 전은 시군구별 rentsum 파일
from jobs.rent_archive import iter_sums
_rfirst = min((r['m'] for r in out['cx_rent']), default='999999')
for r in iter_sums(_store, sorted({s.split('-')[0] for s in SEQS})):
    if r['apt_seq'] in SEQS and int(r['area_group']) in (84, 85) and r['contract_month'] < _rfirst:
        out['cx_rent'].append(dict(apt_seq=r['apt_seq'], m=r['contract_month'], area_group=int(r['area_group']),
                                   **{k: (int(r[k]) if r[k] != '' else None) for k in ('n_jeonse', 'jeonse_median_10k', 'n_jeonse_new', 'jeonse_new_median_10k', 'n_jeonse_renew')}))
out['cx_rent'].sort(key=lambda r: r['m'])
out['cx_phase'] = select(db, f"""SELECT apt_seq, area_group, phase, pattern, chg_12m, up_months, down_months, last3, region_chg_12m, rel_strength,
 jeonse_10k, jeonse_n, jeonse_src, jeonse_24m_10k, jeonse_24m_n, jeonse_24m_approx, reverse_risk, reserve_10k, real_ref_10k, base2020_10k, real_chg_2020,
 households, turnover_pct, turnover_state, e3_seqs, e3_target_10k, e3_chg_12m, rel_strength_e3, e2_ratio, e2_n, e2_basis, e4_cap_10k, e4_cap_n, e4_compress, e4_sizes,
 f1_zone_24m, f1_sgg_24m, f1_ipju, f1_next, d4_jeonse_chg, d4_n, d4_cause, a5_est_10k, a5_from_ag, a5_n, c6_band_hh, c6_band_turn, c6_region_med, c6_reason
 FROM complex_metrics WHERE apt_seq IN ({sl}) AND area_group IN (84,85)""")
out['e3_names'] = select(db, f"""SELECT apt_seq, apt_name FROM complexes WHERE apt_seq IN (
 SELECT unnest(string_to_array(e3_seqs, ',')) FROM complex_metrics WHERE apt_seq IN ({sl}) AND area_group IN (84,85))""")
out['cx_access'] = select(db, f"""SELECT apt_seq, station_name, station_m, h2_cbd_min, h2_cbd_tr, h2_ybd_min, h2_ybd_tr, h2_gbd_min, h2_gbd_tr
 FROM complexes WHERE apt_seq IN ({sl})""")
# E8 상급지까지 거리 (complex_e8, jobs/locality.py) + H3 학원가 규모의 수도권 동 순위 (complexes.academy_exam, 법정동 단위)
out['cx_loc'] = select(db, f"""WITH a AS (SELECT region_code, umd_name, max(academy_exam) ac FROM complexes WHERE academy_exam IS NOT NULL GROUP BY 1, 2),
 r AS (SELECT region_code, umd_name, ac, rank() OVER (ORDER BY ac DESC) rk, count(*) OVER () n FROM a)
SELECT c.apt_seq, c.umd_name, r.ac, r.rk, r.n, d.grade, d.up_dong, d.up_grade, d.up_m, d.top_dong, d.top_m
 FROM complexes c LEFT JOIN r ON r.region_code = c.region_code AND r.umd_name = c.umd_name LEFT JOIN complex_e8 d ON d.apt_seq = c.apt_seq
 WHERE c.apt_seq IN ({sl})""")
# H5 정비사업: 서울 재건축 구역 단계(redev_zone·complex_redev, jobs/redev.py) + 건축물대장(complex_bldg, jobs/bldg.py)
out['cx_redev'] = select(db, f"""SELECT r.apt_seq, z.zone_nm, z.biz_type, z.stage, z.stage_no, z.existing_hh, z.built_hh, z.zone_ymd::text, z.committee_ymd::text,
  z.assoc_ymd::text, z.impl_ymd::text, z.mgmt_ymd::text, z.construction_ymd::text, z.public_private, z.sale_hh, z.gen_sale_est, z.gen_ratio, z.gen_pct
 FROM complex_redev r JOIN redev_zone z USING (code) WHERE r.apt_seq IN ({sl})""")
out['cx_bldg'] = select(db, f"SELECT apt_seq, land_area, land_src, use_zone, price_per_m2, vl_cap, hh, suspect, vl_rat, land_per_hh FROM complex_rebuild WHERE apt_seq IN ({sl})")
# R9 인지도(검색량, complex_search, jobs/searchtrend.py): 지수와 받은 단지 중 백분위
out['cx_search'] = select(db, f"""SELECT apt_seq, keyword, n_months, idx, round((100 * percent_rank() OVER (ORDER BY idx))::numeric, 1) AS pct, fetched_at::text
 FROM complex_search WHERE idx IS NOT NULL""")
out['cx_search'] = [r for r in out['cx_search'] if r['apt_seq'] in SEQS]
# B2 회복 패턴 검증 결과 (b2_validation, jobs/b2_check.py): 백테스트 + 분기 스냅숏 자동 평가
out['b2_validation'] = select(db, "SELECT asof::text, horizon_m, pattern, n, mean_excess, beat_pct, source FROM b2_validation ORDER BY asof, horizon_m, pattern")
# H6 주민 소득 (region_income, jobs/macro.py): 수도권 시군구 1인당 근로소득, 5년 전과 최신
out['income'] = select(db, """SELECT year, sido, name, region_codes, avg_pay_10k FROM region_income
 WHERE year IN ((SELECT max(year) FROM region_income), (SELECT (max(year)::int - 5)::text FROM region_income)) ORDER BY year, avg_pay_10k DESC""")
# C3·C4 하락기 환금성 (complex_liquidity, jobs/liquidity.py)
out['cx_liq'] = select(db, f"""SELECT apt_seq, households, peak_m, trough_m, drop_pct, window_src, down_n, down_turnover, down_rank, up_n, up_turnover, keep_ratio, keep_rank,
  (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY keep_ratio) FROM complex_liquidity x WHERE x.region_code = l.region_code) AS keep_region_med,
  (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY down_turnover) FROM complex_liquidity x WHERE x.region_code = l.region_code) AS down_region_med
 FROM complex_liquidity l WHERE apt_seq IN ({sl})""")
out['cx_zone'] = select(db, f"""SELECT c.apt_seq, z.name, z.e5_ratio, z.e5_n, z.e7_new_ppm, z.e7_mid_ppm, z.e7_old_ppm, z.e7_n, z.f1_react_rel, z.f1_react_n
 FROM complexes c JOIN lifezone z ON z.zone_id = c.lifezone_id WHERE c.apt_seq IN ({sl})""")
# D2. 급지 E1 (dong_grade 최신): 예시 단지의 동 급지·표시 3개
G = "(SELECT * FROM dong_grade WHERE asof = (SELECT max(asof) FROM dong_grade))"
out['cx_grade'] = select(db, f"""SELECT c.apt_seq, c.umd_name, g.grade, g.value_10k, g.q1_10k, g.q3_10k, g.n_complex, g.old_share,
  g.flag_rebuild, g.flag_gap, g.new_big_name, g.new_big_10k, g.asof::text asof, k.households
 FROM complexes c LEFT JOIN {G} g ON g.region_code = c.region_code AND g.umd_name = c.umd_name
 LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code WHERE c.apt_seq IN ({sl})""")
out['cx_rphase'] = select(db, f"SELECT apt_seq, region_name, phase, chg_12m, asof, sido_level FROM complex_region_phase WHERE apt_seq IN ({sl})")
# D3. 후보 단지 찾기 (⑦): 기준 시세가 있는 단지·면적 전체 + 급지·표시
out['cand'] = select(db, f"""SELECT m.apt_seq, m.area_group, coalesce(m.ref_10k, m.a5_est_10k) AS ref_10k, m.ref_10k IS NULL AS est, m.confidence, rp.phase, m.pattern, m.turnover_pct, c.apt_name, c.region_code, c.umd_name,
  c.build_year, k.households, g.grade, g.flag_rebuild, g.flag_gap, g.new_big_name, l.down_rank,
  rb.vl_rat, rb.land_per_hh, rz.stage, rz.stage_no, rz.gen_pct
 FROM complex_metrics m JOIN complexes c USING (apt_seq)
 LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
 LEFT JOIN complex_liquidity l ON l.apt_seq = m.apt_seq
 LEFT JOIN complex_rebuild rb ON rb.apt_seq = m.apt_seq
 LEFT JOIN complex_region_phase rp ON rp.apt_seq = m.apt_seq   -- ⑦ 국면 필터 = 지역 B1(R-ONE). 단지 B1 은 백테스트에서 예측력 없음(2026-10-20)
 LEFT JOIN LATERAL (SELECT z.stage, z.stage_no, z.gen_pct FROM complex_redev r JOIN redev_zone z USING (code)
                    WHERE r.apt_seq = m.apt_seq ORDER BY z.stage_no DESC NULLS LAST LIMIT 1) rz ON true
 LEFT JOIN {G} g ON g.region_code = c.region_code AND g.umd_name = c.umd_name
 WHERE (m.ref_10k IS NOT NULL OR m.a5_est_10k IS NOT NULL) AND m.area_group BETWEEN 40 AND 135""")
# E. R-ONE 주간 지수 (rone_weekly, jobs/rone.py)
out['rone'] = select(db, """SELECT w.stat, w.cls_id, r.full_name, r.region_code, w.week_id, w.week_date::text d, w.value
 FROM rone_weekly w JOIN rone_regions r USING (cls_id)
 WHERE w.stat IN ('sale','jeonse') AND (r.region_code IS NOT NULL OR r.cls_id IN (50008, 50002))
   AND w.week_date >= (SELECT max(week_date) FROM rone_weekly) - 380""")
out['rone_series'] = select(db, """SELECT stat, cls_id, week_date::text d, value FROM rone_weekly
 WHERE stat IN ('sale','jeonse') AND cls_id IN (50008, 50002) ORDER BY week_date""")
# F. 시장 체크리스트 신호 (market_signals, jobs/market.py) + 거시 최근 25개월 (macro_monthly)
out['signals'] = select(db, "SELECT key, asof::text asof, value, state, detail FROM market_signals")
out['macro'] = select(db, """SELECT series, period, value FROM macro_monthly
 WHERE period >= to_char(now() - interval '26 months', 'YYYYMM') ORDER BY series, period""")
out['auction'] = select(db, """SELECT period_month, area_code, sale_ratio, source_url FROM auction_stats
 WHERE source = 'ggi_news' AND use_type = '아파트' ORDER BY period_month""")
# F3. 시군구 미분양(unsold_sgg) + 최근 24개월 민영 공고 분양가 ÷ 주변 시세(presale) + 앞으로 24개월 입주 예정(ipju_plan)
out['unsold'] = select(db, """
WITH lp AS (SELECT max(period) p FROM unsold_sgg),
u AS (SELECT sido, name, region_codes, unsold, unsold_done FROM unsold_sgg, lp WHERE period = lp.p),
u0 AS (SELECT sido, name, unsold AS u0 FROM unsold_sgg, lp WHERE period = to_char(to_date(lp.p, 'YYYYMM') - INTERVAL '12 months', 'YYYYMM')),
pr AS (SELECT u.sido, u.name, count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY ps.price_ratio) AS r,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY ps.price_ratio_new) AS rn
       FROM u JOIN presale ps ON ps.region_code = ANY (string_to_array(u.region_codes, ',')) WHERE ps.price_ratio IS NOT NULL GROUP BY 1, 2),
ip AS (SELECT u.sido, u.name, sum(i.households) AS hh FROM u JOIN ipju_plan i ON i.region_code = ANY (string_to_array(u.region_codes, ','))
       WHERE i.move_in_ym BETWEEN to_char(now(), 'YYYYMM') AND to_char(now() + INTERVAL '23 months', 'YYYYMM') GROUP BY 1, 2)
SELECT (SELECT p FROM lp) AS period, u.sido, u.name, u.unsold, u0.u0, u.unsold_done, pr.n, pr.r, pr.rn, ip.hh
FROM u LEFT JOIN u0 USING (sido, name) LEFT JOIN pr USING (sido, name) LEFT JOIN ip USING (sido, name)
WHERE u.region_codes IS NOT NULL ORDER BY u.unsold DESC""")
# H4 역 단위: 철도 사업 역(기존 좌표가 있는 역) 700m 안 단지 (📖 역세권 p.220)
PS = """(SELECT p.name, p.status, s.name AS st, s.lat, s.lng FROM transit_projects p
  CROSS JOIN unnest(string_to_array(p.stations, ',')) u(n) JOIN station s ON s.name = u.n)"""
NEAR = "c.lat IS NOT NULL AND abs(c.lat - ps.lat) < 0.007 AND abs(c.lng - ps.lng) < 0.009 AND 111320 * sqrt(power(c.lat - ps.lat, 2) + power((c.lng - ps.lng) * 0.7934, 2)) <= 700"
out['cx_proj'] = select(db, f"""SELECT c.apt_seq, ps.name, ps.status, ps.st,
  round(111320 * sqrt(power(c.lat - ps.lat, 2) + power((c.lng - ps.lng) * 0.7934, 2))) AS m
 FROM complexes c JOIN {PS} ps ON {NEAR} WHERE c.apt_seq IN ({sl}) ORDER BY 1, 5""")
out['cand_proj'] = select(db, f"""SELECT DISTINCT c.apt_seq FROM complexes c JOIN {PS} ps ON {NEAR} WHERE ps.status IN ('착공', '확정')""")
out['price_bands'] = __import__('jobs.market', fromlist=['price_bands']).price_bands(db)
# 지역 월별 (region_monthly, jobs/region_stats.py): 소비심리 2년, 전세가율 서울·수도권 2년 + 시군구 최신, 예시 단지 시군구 인구(12월)
out['region_monthly'] = select(db, f"""SELECT series, region, period, value FROM region_monthly
 WHERE (series IN ('sentiment', 'jeonse_ratio') AND region IN ('11', '28', '41', 'SUDO', 'KR') AND period >= to_char(now() - interval '26 months', 'YYYYMM'))
    OR (series = 'jeonse_ratio' AND period = (SELECT max(period) FROM region_monthly WHERE series = 'jeonse_ratio'))
    OR (series LIKE 'pop_%' AND period LIKE '%12' AND region IN (SELECT DISTINCT split_part(s, '-', 1) FROM unnest(ARRAY[{sl}]) s))
 ORDER BY series, region, period""")
# 풍선효과 (balloon, jobs/balloon.py)
out['balloon'] = select(db, """SELECT event_date::text e, region_code rc, grp, chg_13w, chg_26w, weeks_now, chg_now, outsider_before ob, outsider_after oa,
  seoul_before sb, seoul_after sa FROM balloon ORDER BY event_date, grp, chg_now DESC""")
out['balloon_path'] = select(db, "SELECT event_date::text e, grp, week, median_chg m, n FROM balloon_path ORDER BY event_date, grp, week")
out['policy_events'] = select(db, "SELECT event_date::text d, kind, title, source FROM policy_events ORDER BY event_date")
# G. 유동성·소득·집값 (G1): 2005년부터 전체
out['g1'] = select(db, """SELECT series, period, value FROM macro_monthly
 WHERE series IN ('m2', 'household_income', 'apt_kb_nat', 'apt_kb_seoul', 'base_rate') AND period >= '2004' ORDER BY series, period""")
# H. E6 갈아타기 격차: 단지별 전용 84~85㎡(면적군 84·85) 중개·비해제·1층 제외 분기 중앙가. 과거 파일(2020~2024-09) + DB(2024-10~)
import glob, gzip, csv as _csv
from statistics import median as _med
_q = lambda ym: f"{ym[:4]}Q{(int(ym[4:6]) - 1) // 3 + 1}"
_v: dict = {}
for f in sorted(glob.glob(os.path.join((os.environ.get('HC_ARCHIVE') or '').removeprefix('dir:') or str(ROOT / 'data/archive'), 'deals_hist_*.csv.gz'))):
    for r in _csv.DictReader(gzip.open(f, 'rt', encoding='utf-8')):
        if r['is_cancelled'] in ('1', 'True', 'true') or r['deal_type'] != '중개' or r.get('floor') == '1' or not r['area_m2'] or math.floor(float(r['area_m2'])) not in (84, 85):
            continue
        _v.setdefault((r['apt_seq'], _q(r['contract_month'])), []).append(int(r['price_10k']))
e6 = {}
for (a, q), v in _v.items():
    e6.setdefault(a, {})[q] = _med(v)
for r in select(db, """SELECT apt_seq, substr(contract_month,1,4)||'Q'||((substr(contract_month,5,2)::int-1)/3+1) q,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) p FROM deals
  WHERE NOT is_cancelled AND deal_type = '중개' AND floor IS DISTINCT FROM 1 AND area_group IN (84, 85) GROUP BY 1, 2"""):
    e6.setdefault(r['apt_seq'], {})[r['q']] = float(r['p'])
out['e6'] = e6
out['e6_names'] = select(db, "SELECT apt_seq, apt_name, region_code, umd_name FROM complexes")
# E6 서버 계산 갈아타기 목표 후보 (e6_targets, jobs/gap.py)
out['e6_targets'] = select(db, "SELECT apt_seq, rank, target_seq, ratio_now, gap_pct, dist_m FROM e6_targets ORDER BY apt_seq, rank")
out['seqs'] = SEQS
out['regions'] = {k: v for k, v in REGIONS.items()}
json.dump(out, open(OUT / 'raw.json', 'w'), ensure_ascii=False, default=str)
print({k: len(v) for k, v in out.items()})
