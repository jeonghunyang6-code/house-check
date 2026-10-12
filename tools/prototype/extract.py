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
out['monthly'] = select(db, """
 SELECT contract_month m, count(*) FILTER (WHERE NOT is_cancelled) n,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY price_10k) FILTER (WHERE NOT is_cancelled AND deal_type='중개' AND area_group IN (84,85)) p84
 FROM deals WHERE region_code LIKE '11%' GROUP BY 1 ORDER BY 1""")
# B. 오늘 처음 등록된 거래 + 전고점 (직거래·해제 제외, 4.3)
PREV = """(SELECT max(p.price_10k) FROM deals p WHERE p.apt_seq=d.apt_seq AND p.area_group=d.area_group
           AND p.contract_date < d.contract_date AND NOT p.is_cancelled AND p.deal_type='중개')"""
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
out['cx_rent'] = select(db, f"""SELECT apt_seq, contract_month m, area_group, n_jeonse, jeonse_median_10k, n_jeonse_new, jeonse_new_median_10k, n_jeonse_renew
 FROM rent_monthly WHERE apt_seq IN ({sl}) AND area_group IN (84,85) ORDER BY contract_month""")
out['cx_phase'] = select(db, f"""SELECT apt_seq, area_group, phase, chg_12m, up_months, down_months, last3, region_chg_12m, rel_strength
 FROM complex_metrics WHERE apt_seq IN ({sl}) AND area_group IN (84,85)""")
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
# G. 유동성·소득·집값 (G1): 2005년부터 전체
out['g1'] = select(db, """SELECT series, period, value FROM macro_monthly
 WHERE series IN ('m2', 'household_income', 'apt_kb_nat', 'apt_kb_seoul', 'base_rate') AND period >= '2004' ORDER BY series, period""")
out['seqs'] = SEQS
out['regions'] = {k: v for k, v in REGIONS.items()}
json.dump(out, open(OUT / 'raw.json', 'w'), ensure_ascii=False, default=str)
print({k: len(v) for k, v in out.items()})
