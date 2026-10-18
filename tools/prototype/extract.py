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
SEQS = ['11710-8865','11740-4628','11200-3120','11590-3954','11410-4479','11230-2587','11500-5419','11350-133']
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
out['cx_phase'] = select(db, f"""SELECT apt_seq, area_group, phase, pattern, chg_12m, up_months, down_months, last3, region_chg_12m, rel_strength,
 jeonse_10k, jeonse_24m_10k, jeonse_24m_n, reverse_risk, reserve_10k, real_ref_10k, base2020_10k, real_chg_2020,
 households, turnover_pct, turnover_state, e3_seqs, e3_target_10k, e3_chg_12m, rel_strength_e3, e2_ratio, e2_n, e2_basis, e4_cap_10k, e4_cap_n, e4_compress, e4_sizes,
 f1_zone_24m, f1_sgg_24m, f1_ipju, f1_next
 FROM complex_metrics WHERE apt_seq IN ({sl}) AND area_group IN (84,85)""")
out['e3_names'] = select(db, f"""SELECT apt_seq, apt_name FROM complexes WHERE apt_seq IN (
 SELECT unnest(string_to_array(e3_seqs, ',')) FROM complex_metrics WHERE apt_seq IN ({sl}) AND area_group IN (84,85))""")
out['cx_access'] = select(db, f"""SELECT apt_seq, station_name, station_m, h2_cbd_min, h2_cbd_tr, h2_ybd_min, h2_ybd_tr, h2_gbd_min, h2_gbd_tr
 FROM complexes WHERE apt_seq IN ({sl})""")
out['cx_zone'] = select(db, f"""SELECT c.apt_seq, z.name, z.e5_ratio, z.e5_n, z.e7_new_ppm, z.e7_mid_ppm, z.e7_old_ppm, z.e7_n, z.f1_react_rel, z.f1_react_n
 FROM complexes c JOIN lifezone z ON z.zone_id = c.lifezone_id WHERE c.apt_seq IN ({sl})""")
# D2. 급지 E1 (dong_grade 최신): 예시 단지의 동 급지·표시 3개
G = "(SELECT * FROM dong_grade WHERE asof = (SELECT max(asof) FROM dong_grade))"
out['cx_grade'] = select(db, f"""SELECT c.apt_seq, c.umd_name, g.grade, g.value_10k, g.q1_10k, g.q3_10k, g.n_complex, g.old_share,
  g.flag_rebuild, g.flag_gap, g.new_big_name, g.new_big_10k, g.asof::text asof, k.households
 FROM complexes c LEFT JOIN {G} g ON g.region_code = c.region_code AND g.umd_name = c.umd_name
 LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code WHERE c.apt_seq IN ({sl})""")
# D3. 후보 단지 찾기 (⑦): 기준 시세가 있는 단지·면적 전체 + 급지·표시
out['cand'] = select(db, f"""SELECT m.apt_seq, m.area_group, m.ref_10k, m.confidence, m.phase, m.pattern, m.turnover_pct, c.apt_name, c.region_code, c.umd_name,
  c.build_year, k.households, g.grade, g.flag_rebuild, g.flag_gap, g.new_big_name
 FROM complex_metrics m JOIN complexes c USING (apt_seq)
 LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
 LEFT JOIN {G} g ON g.region_code = c.region_code AND g.umd_name = c.umd_name
 WHERE m.ref_10k IS NOT NULL AND m.area_group BETWEEN 40 AND 135""")
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
# G. 유동성·소득·집값 (G1): 2005년부터 전체
out['g1'] = select(db, """SELECT series, period, value FROM macro_monthly
 WHERE series IN ('m2', 'household_income', 'apt_kb_nat', 'apt_kb_seoul', 'base_rate') AND period >= '2004' ORDER BY series, period""")
# H. E6 갈아타기 격차: 단지별 전용 84~85㎡(면적군 84·85) 중개·비해제 분기 중앙가. 과거 파일(2020~2024-09) + DB(2024-10~)
import glob, gzip, csv as _csv
from statistics import median as _med
_q = lambda ym: f"{ym[:4]}Q{(int(ym[4:6]) - 1) // 3 + 1}"
_v: dict = {}
for f in sorted(glob.glob(os.path.join((os.environ.get('HC_ARCHIVE') or '').removeprefix('dir:') or str(ROOT / 'data/archive'), 'deals_hist_*.csv.gz'))):
    for r in _csv.DictReader(gzip.open(f, 'rt', encoding='utf-8')):
        if r['is_cancelled'] in ('1', 'True', 'true') or r['deal_type'] != '중개' or not r['area_m2'] or math.floor(float(r['area_m2'])) not in (84, 85):
            continue
        _v.setdefault((r['apt_seq'], _q(r['contract_month'])), []).append(int(r['price_10k']))
e6 = {}
for (a, q), v in _v.items():
    e6.setdefault(a, {})[q] = _med(v)
for r in select(db, """SELECT apt_seq, substr(contract_month,1,4)||'Q'||((substr(contract_month,5,2)::int-1)/3+1) q,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) p FROM deals
  WHERE NOT is_cancelled AND deal_type = '중개' AND area_group IN (84, 85) GROUP BY 1, 2"""):
    e6.setdefault(r['apt_seq'], {})[r['q']] = float(r['p'])
out['e6'] = e6
out['e6_names'] = select(db, "SELECT apt_seq, apt_name, region_code, umd_name FROM complexes")
out['seqs'] = SEQS
out['regions'] = {k: v for k, v in REGIONS.items()}
json.dump(out, open(OUT / 'raw.json', 'w'), ensure_ascii=False, default=str)
print({k: len(v) for k, v in out.items()})
