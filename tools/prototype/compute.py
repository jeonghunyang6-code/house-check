"""raw.json → data.json (시안에 넣을 계산 결과). 지표 정의는 docs/insights/indicators.md A1·B1·B2·D1, ARCHITECTURE 4.3."""
import json, statistics as st, sys
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'tools/prototype/out'
d = json.load(open(OUT / 'raw.json'))
TODAY = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
REG = d['regions']

def months(a, b):
    y, m = int(a[:4]), int(a[4:]); out = []
    while (y, m) <= (int(b[:4]), int(b[4:])):
        out.append(f"{y}{m:02d}"); y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out

ALL = months('202001', '202610')
GAP = set()  # 2026-10-12 backfill 로 공백 해소
mon = {r['m']: r for r in d['monthly']}
monthly = [{'m': m, 'n': (mon[m]['n'] if m in mon else None), 'p84': (round(mon[m]['p84']) if m in mon and mon[m]['p84'] else None),
            'gap': m in GAP, 'partial': m in ('202609', '202610')} for m in ALL]

def band(price):  # D1 정상 범위 (책 p.152), 사이 가격대는 선형 보간
    pts = [(0, (60, 90)), (50000, (60, 90)), (80000, (50, 60)), (150000, (50, 60)), (200000, (30, 50)), (10**9, (30, 50))]
    for (x0, r0), (x1, r1) in zip(pts, pts[1:]):
        if x0 <= price <= x1:
            t = 0 if x1 == x0 else (price - x0) / (x1 - x0)
            return [round(r0[0] + (r1[0] - r0[0]) * t), round(r0[1] + (r1[1] - r0[1]) * t)]


RM = {}
for _r in d.get('region_monthly', []):
    RM.setdefault((_r['series'], _r['region']), []).append((_r['period'], float(_r['value'])))
def reg(rc):
    """같은 시군구 전세가율(최신)과 인구 5년 변화(12월끼리). D1 지역값을 단지값 옆에 (M5), H3 학령인구·D7 생산가능인구."""
    jr = RM.get(('jeonse_ratio', rc), [])
    out = {'jr': jr[-1] if jr else None, 'jr_seoul': (RM.get(('jeonse_ratio', '11')) or [None])[-1]}
    for k in ('school', 'working', 'total'):
        ps = RM.get((f'pop_{k}', rc), [])
        if len(ps) >= 6:
            out[k] = [ps[-6][0], ps[-6][1], ps[-1][0], ps[-1][1]]
    return out
from collector.policy import regulated_now, zones_for
from collector.projects import PROJECTS
import calendar
def liq(seq, gr):
    """C3·C4 (complex_liquidity) + 상승기에 걸린 토지거래허가구역 (collector/policy.py)."""
    z = next((x for x in d.get('cx_liq', []) if x['apt_seq'] == seq), None)
    if not z:
        return None
    o = {k: (float(v) if isinstance(v, str) and k not in ('peak_m', 'trough_m', 'window_src') else v) for k, v in z.items() if k != 'apt_seq'}
    y, m = int(o['peak_m'][:4]), int(o['peak_m'][4:])
    zs = zones_for(seq[:5], gr and gr['umd_name'], date(2020, 1, 1), date(y, m, calendar.monthrange(y, m)[1]), kind='토허')
    o['toh'] = [f"{zz.start:%Y.%m}~ {zz.note.split('.')[0]}{' (구역이 동 일부라 이 단지가 들어가는지 확인 필요)' if zz.scope == 'part' else ''}" for zz in zs]
    return o

cx = []
for seq in d['seqs']:
    deals = [r for r in d['cx_deals'] if r['apt_seq'] == seq]
    ok = [r for r in deals if not r['is_cancelled'] and r['deal_type'] == '중개']
    okr = [r for r in ok if r['floor'] != 1]  # 기준 시세용: 1층 제외 (sql/metrics.sql base)
    name = deals[-1]['apt_name']
    bym = {}
    for r in okr: bym.setdefault(r['cd'][:7].replace('-', ''), []).append(r['price_10k'])
    ref = []  # 3개월 이동 중앙값 (B1·B2 의 월별 기준 시세)
    for i, m in enumerate(ALL):
        win = sum((bym.get(x, []) for x in ALL[max(0, i - 2):i + 1]), [])
        ref.append({'m': m, 'v': round(st.median(win)) if win and m not in GAP else None, 'n': len(bym.get(m, []))})
    def rng(a, b, f):
        vs = [x['v'] for x in ref if a <= x['m'] <= b and x['v']]
        return f(vs) if vs else None
    P, T = rng('202101', '202206', max), rng('202207', '202306', min)
    # A1 기준 시세: 최근 60일 중앙값, 3건 미만이면 90→180일
    C = conf = cdays = None
    for days, c in ((60, '높음'), (90, '보통'), (180, '낮음')):
        w = [r['price_10k'] for r in okr if date.fromisoformat(r['cd']) > TODAY - timedelta(days=days)]
        if len(w) >= 3: C, conf, cn, cdays = round(st.median(w)), c, len(w), days; break
    # 자료 충분도 근거 (sql/metrics.sql 2-1): 창 안 가격 범위, 뺀 1층 건수, 마지막 거래일(1층 포함)
    cwin = [r for r in ok if cdays and date.fromisoformat(r['cd']) > TODAY - timedelta(days=cdays)]
    cspread = cdays and {'days': cdays, 'lo': min(r['price_10k'] for r in cwin if r['floor'] != 1),
                         'hi': max(r['price_10k'] for r in cwin if r['floor'] != 1),
                         'f1': sum(r['floor'] == 1 for r in cwin), 'last': max(r['cd'] for r in ok)}
    rec = (C - T) / (P - T) if (C and P and T and P > T) else None
    # B2 회복 패턴은 서버(sql/metrics.sql, 국면 조건 포함) 값을 그대로 쓴다. 위 P·T·rec 는 차트 표시용
    srv = [r for r in d.get('cx_phase', []) if r['apt_seq'] == seq and r['area_group'] in (84, 85) and r.get('pattern')]
    pattern = max(srv, key=lambda r: r['area_group'] == 84)['pattern'] if srv else None
    rents = [r for r in d['cx_rent'] if r['apt_seq'] == seq]
    jm = {}
    for r in rents:
        if r['n_jeonse'] and r['jeonse_median_10k']:
            jm.setdefault(r['m'], []).append((r['n_jeonse'], r['jeonse_median_10k']))
    jser = [{'m': m, 'v': round(sum(n * v for n, v in jm[m]) / sum(n for n, _ in jm[m]))} for m in ALL if m in jm]
    cur = [r for r in rents if r['m'] in ('202609', '202610')]
    new = [(r['n_jeonse_new'], r['jeonse_new_median_10k']) for r in cur if r['n_jeonse_new'] and r['jeonse_new_median_10k']]
    allj = [(r['n_jeonse'], r['jeonse_median_10k']) for r in cur if r['n_jeonse'] and r['jeonse_median_10k']]
    nb = band(C) if C else None
    n12 = sum(1 for r in ok if date.fromisoformat(r['cd']) > TODAY - timedelta(days=365))
    phs = [r for r in d.get('cx_phase', []) if r['apt_seq'] == seq and r['phase']]
    ph = max(phs, key=lambda r: r['area_group'] == 84) if phs else None  # 84 우선
    m84 = [r for r in d.get('cx_phase', []) if r['apt_seq'] == seq and r['area_group'] in (84, 85)]
    m84 = max(m84, key=lambda r: r['area_group'] == 84) if m84 else None
    gr = next((g for g in d.get('cx_grade', []) if g['apt_seq'] == seq), None)
    if m84 and m84.get('jeonse_n'):  # 서버(sql/metrics.sql js)가 원본 계약으로 계산한 실제 중앙값
        J, jn, jsrc, japprox = m84['jeonse_10k'], m84['jeonse_n'], m84['jeonse_src'], False
    else:  # 서버 값이 없으면 월별 중앙값의 건수 가중 평균(근사)
        src = new or allj
        J = round(sum(n * v for n, v in src) / sum(n for n, _ in src)) if src else None
        jn, jsrc, japprox = sum(n for n, _ in src) if src else 0, '신규' if new else '전체', True
    ratio = J / C * 100 if (J and C) else None
    cx.append({'grade': gr and gr['grade'] is not None and {k: gr[k] for k in ('umd_name', 'grade', 'value_10k', 'q1_10k', 'q3_10k', 'n_complex', 'old_share', 'flag_rebuild', 'flag_gap', 'new_big_name', 'new_big_10k', 'asof')},
               'hh': gr and gr['households'],
               'm': m84 and {k: m84.get(k) for k in ('jeonse_24m_10k', 'jeonse_24m_n', 'jeonse_24m_approx', 'reverse_risk', 'reserve_10k', 'real_ref_10k', 'base2020_10k', 'real_chg_2020',
               'turnover_pct', 'turnover_state', 'e3_target_10k', 'e3_chg_12m', 'rel_strength_e3', 'e2_ratio', 'e2_n', 'e2_basis', 'e4_cap_10k', 'e4_cap_n', 'e4_compress', 'e4_sizes', 'f1_zone_24m', 'f1_sgg_24m', 'f1_ipju', 'f1_next')},
               'acc': next(({k: z[k] for k in ('station_name', 'station_m', 'h2_cbd_min', 'h2_cbd_tr', 'h2_ybd_min', 'h2_ybd_tr', 'h2_gbd_min', 'h2_gbd_tr')} for z in d.get('cx_access', []) if z['apt_seq'] == seq), None),
               'liq': liq(seq, gr),
               'reg': reg(seq[:5]),
               'zone': next(({k: z[k] for k in ('name', 'e5_ratio', 'e5_n', 'e7_new_ppm', 'e7_mid_ppm', 'e7_old_ppm', 'e7_n', 'f1_react_rel', 'f1_react_n')} for z in d.get('cx_zone', []) if z['apt_seq'] == seq), None),
               'e3': m84 and m84['e3_seqs'] and [n['apt_name'] for n in d.get('e3_names', []) if n['apt_seq'] in m84['e3_seqs'].split(',')],
               'phase': ph and {k: ph[k] for k in ('phase', 'chg_12m', 'up_months', 'down_months', 'last3', 'region_chg_12m', 'rel_strength')}, 'seq': seq, 'name': name, 'region': REG[seq[:5]], 'P': P, 'T': T, 'C': C, 'conf': conf, 'cn': cn if C else 0, 'cs': cspread,
               'rec': rec, 'pattern': pattern, 'J': J, 'jn': jn, 'jsrc': jsrc, 'japprox': japprox, 'ratio': ratio, 'band': nb,
               'n12': n12, 'ref': ref,
               'pts': [[r['cd'], r['price_10k'], r['floor']] for r in ok],
               'jser': jser})

def status(r):
    seoul = r['region_code'].startswith('11')
    if r['is_cancelled']: return 'cancelled'
    if r['deal_type'] != '중개': return 'direct'
    if not seoul: return 'short'          # 경기·인천: 이력이 2026-09부터라 전고점 판정 보류
    if r['prev_high'] is None: return 'first'
    return 'high' if r['price_10k'] > r['prev_high'] else 'below'
today = [{**r, 'region': REG[r['region_code']], 'status': status(r)} for r in d['today']]
rh = d['recent_highs']

# R-ONE 주간: 최신 주 대비 직전 주(주간), 52주 전 이전의 가장 가까운 주(연간). 연속 상승 주수는 서울·수도권 시계열에서.
def weekly():
    rows = d['rone']
    dates = sorted({r['d'] for r in rows})
    if len(dates) < 2:
        return None
    last, prev = dates[-1], dates[-2]
    yd = [x for x in dates if x <= (date.fromisoformat(last) - timedelta(days=364)).isoformat()]
    year = yd[-1] if yd else None
    qd = [x for x in dates if x <= (date.fromisoformat(last) - timedelta(days=91)).isoformat()]
    q13 = qd[-1] if qd else None  # D2: 13주(약 3개월) 전 발표 주
    val = {(r['stat'], r['cls_id'], r['d']): r['value'] for r in rows}
    v = {}
    for r in rows:
        if r['region_code'] and r['d'] == last:
            k = 't' if r['stat'] == 'sale' else 'j'
            a, b = r['value'], val.get((r['stat'], r['cls_id'], prev))
            y = val.get((r['stat'], r['cls_id'], year)) if year else None
            v.setdefault(r['region_code'], {})[k] = round((a / b - 1) * 100, 2) if b else None
            v[r['region_code']]['y' + k] = round((a / y - 1) * 100, 2) if y else None
            q = val.get((r['stat'], r['cls_id'], q13)) if q13 else None
            v[r['region_code']]['q' + k] = round((a / q - 1) * 100, 2) if q else None
    tot = {}
    for stat, k in (('sale', 't'), ('jeonse', 'j')):
        for cls, nm in ((50008, 'seoul'), (50002, 'sudo')):
            s = [x['value'] for x in d['rone_series'] if x['stat'] == stat and x['cls_id'] == cls]
            n = 0
            for i in range(len(s) - 1, 0, -1):
                if s[i] > s[i - 1]: n += 1
                else: break
            tot[f'{nm}_{k}'] = {'w': round((s[-1] / s[-2] - 1) * 100, 2), 'streak': n, 'weeks': len(s)}
    from collector.regions import REGIONS
    return {'date': last, 'prev_date': prev, 'year_date': year, 'q13_date': q13, 'v': v, 'tot': tot,
            'nodata': [c for c in REGIONS if c not in v and c != '28720']}

def g1():  # 유동성·소득·집값 2005 = 100 (📖 p.50), collector/market.py rebase
    from collector.market import rebase
    out = {}
    for k in ('m2', 'household_income', 'apt_kb_nat', 'apt_kb_seoul'):
        out[k] = [[p, v] for p, v in rebase([(r['period'], float(r['value'])) for r in d['g1'] if r['series'] == k])]
    return out

def g2():  # 금리와 집값 (📖 p.48~49): 기준금리, 서울 아파트(KB) 전년비, 달마다 동행/역행
    from collector.market import rate_price_relation, yoy_series
    ser = lambda k: [(r['period'], float(r['value'])) for r in d['g1'] if r['series'] == k]
    rate, kb = ser('base_rate'), ser('apt_kb_seoul')
    yy = [p for p in yoy_series(kb) if p[0] >= '200601']
    return {'rate': [[p, v] for p, v in rate if p >= '200601'], 'yoy': [[p, v] for p, v in yy],
            'rel': [[p, x] for p, x in rate_price_relation(rate, kb) if p >= '200601']}

def e6():
    """E6: 최근 끝난 20분기 84㎡ 분기 중앙가. 🔧 12분기 이상 값이 있고 마지막 2분기 중 하나에 값이 있는 단지만."""
    y, q = TODAY.year, (TODAY.month - 1) // 3      # 이번 분기 바로 전(끝난 분기)
    if q == 0:
        y, q = y - 1, 4
    qs = []
    for _ in range(20):
        qs.append(f"{y}Q{q}")
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    qs.reverse()
    nm = {r['apt_seq']: r for r in d.get('e6_names', [])}
    rows = []
    for a, v in d.get('e6', {}).items():
        if a not in nm or sum(1 for x in qs if x in v) < 12 or not (qs[-1] in v or qs[-2] in v):
            continue
        r = nm[a]
        rows.append([r['apt_name'], r['region_code'], r['umd_name'], [round(v[x]) if x in v else None for x in qs]])
    rows.sort(key=lambda r: (r[1], r[0]))
    return {'q': qs, 'cx': rows}

from collector.regions import REGIONS
json.dump({'monthly': monthly, 'cx': cx, 'today': today,
           'recent': {'n': len(rh), 'highs': sum(r['price_10k'] > r['prev_high'] for r in rh)},
           'weekly': weekly(), 'signals': {r['key']: r for r in d['signals']},
           'macro': {k: [[r['period'], float(r['value'])] for r in d['macro'] if r['series'] == k] for k in {r['series'] for r in d['macro']}},
           'g1': g1(), 'g2': g2(), 'e6': e6(),
           'unsold': [{k: (float(r[k]) if isinstance(r[k], str) and k in ('r', 'rn') else r[k]) for k in r} for r in d.get('unsold', [])],
           'policy': [[r['d'], r['kind'], r['title']] for r in d.get('policy_events', [])],
           'sentiment': {k: v for (sr, k), v in RM.items() if sr == 'sentiment'},
           'reg_now': regulated_now(TODAY),
           # H4 호재 단계 [이름, 단계, 단계 날짜, 전망, 업무지구, 시군구들, 출처] (collector/projects.py)
           'projects': [[p.name, p.status, p.status_date and p.status_date.isoformat(), p.outlook, list(p.cbd), list(p.region_codes), p.source] for p in PROJECTS],
           # 풍선효과: 사건별 [시군구, 그룹, 13주, 26주, 주 수, 지금까지, 외지인 전, 후, 서울 전, 후] / 그룹 중앙값 경로 [그룹, 주, 중앙값, n]
           'balloon': {e: {'rows': [[r['rc'], r['grp'], *[r[k] and float(r[k]) for k in ('chg_13w', 'chg_26w')], r['weeks_now'],
                                     *[r[k] and float(r[k]) for k in ('chg_now', 'ob', 'oa', 'sb', 'sa')]] for r in d.get('balloon', []) if r['e'] == e],
                           'path': [[r['grp'], r['week'], float(r['m']), r['n']] for r in d.get('balloon_path', []) if r['e'] == e]}
                       for e in sorted({r['e'] for r in d.get('balloon', [])})},
           'auction': {a: [[r['period_month'].replace('-', ''), float(r['sale_ratio']) * 100] for r in d.get('auction', []) if r['area_code'] == a]
                       for a in ('서울', '경기', '인천', '전국')},
           # ⑦ 후보 단지: [단지, 시군구, 동, 면적군, 기준 시세(만원), 신뢰도, 국면, 급지, 재건축 기대, 동 안 격차, 신축 대단지, 세대수, 준공, 월 회전율 %, 하락기 거래 시군구 안 분위(C3)]
           'cand': [[r['apt_name'], r['region_code'], r['umd_name'], r['area_group'], r['ref_10k'], r['confidence'], r['phase'], r['grade'],
                     bool(r['flag_rebuild']), bool(r['flag_gap']), r['new_big_name'] == r['apt_name'] if r['new_big_name'] else False,
                     r['households'], r['build_year'], r['turnover_pct'] and float(r['turnover_pct']),
                     r.get('down_rank') and float(r['down_rank'])] for r in d.get('cand', [])],
           'geo': json.load(open(ROOT / 'data/geo/sudogwon_sgg_20260701.json')),
           'region_names': REGIONS, 'asof': TODAY.isoformat()}, open(OUT / 'data.json', 'w'), ensure_ascii=False)
for c in cx: print(c['name'], c['region'], c['P'], c['T'], c['C'], c['conf'], c['cn'], c['pattern'], c['rec'] and round(c['rec'],2), c['J'], c['jn'], c['ratio'] and round(c['ratio']), c['band'], c['n12'])
print('today statuses', {s: sum(t['status'] == s for t in today) for s in set(t['status'] for t in today)})
