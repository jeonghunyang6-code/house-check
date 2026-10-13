"""급지(E1) 분석 스크립트 — 대화 분석용, 아직 DB·시안에 연결 안 됨 (2026-10-13).

확정 방식(사용자 합의): `python tools/analysis/grade_e1.py 0.3 noage` → 연식 보정 없음, 300세대 미만 소단지 거래 가중치 0.3,
경계(84㎡ 환산 실거래 대표가) 30 / 25 / 20 / 15 / 12 / 9 / 6억 8단계 (아래 T 는 옛 경계라 비교 출력용).
입력 $E1_DIR/e1_rows.json 은 아래 SQL 결과(collector.db select):

WITH t AS (SELECT d.apt_seq, d.region_code, x.umd_name, x.build_year, x.kapt_code, d.price_10k*84.0/d.area_m2 p84
  FROM deals d JOIN complexes x USING (apt_seq)
  WHERE NOT d.is_cancelled AND d.deal_type='중개' AND d.area_m2 BETWEEN 40 AND 135 AND d.contract_date > DATE '2026-10-13'-365
    AND x.umd_name IS NOT NULL AND x.build_year IS NOT NULL)
SELECT t.apt_seq, t.region_code, t.umd_name, max(t.build_year) by, percentile_cont(.5) WITHIN GROUP (ORDER BY p84) p,
  count(*) n, max(k.households) hh, max(t.kapt_code) kc
FROM t LEFT JOIN kapt_complexes k ON k.kapt_code=t.kapt_code GROUP BY 1,2,3 HAVING count(*)>=2
"""
import os
import json, sys, statistics as st
from collections import defaultdict, Counter
sys.path.insert(0,'/home/user/house-check')
from collector.regions import REGIONS
rows=json.load(open(os.environ.get('E1_DIR','/tmp/e1')+'/e1_rows.json'))
SMALL_W=float(sys.argv[1]) if len(sys.argv)>1 else 0.3
def b(y):
    a=2026-int(y); return '신축' if a<=5 else '준신축' if a<=15 else '구축A' if a<=20 else '구축B' if a<30 else '30년+'
def small(r):
    if r['hh'] is None: return int(r['n'])<20     # K-apt 미연결: 1년 거래 20건 미만이면 소단지로 본다
    return int(r['hh'])<300
# 300세대+ 단지끼리 동 안에서 잰 비율의 중앙값 (2026-10-13, 동 준신축 기준가 10억 미만 lo / 이상 hi)
FB={'lo':{'신축':1.18,'준신축':1,'구축A':0.81,'구축B':0.70,'30년+':1.0},'hi':{'신축':1.07,'준신축':1,'구축A':0.85,'구축B':0.74,'30년+':1.0}}
CLIP={'신축':(1.0,1.5),'구축A':(0.6,1.0),'구축B':(0.6,1.0)}
MEASURE=len(sys.argv)<3 or sys.argv[2] not in ('nomeasure','noage')
if len(sys.argv)>2 and sys.argv[2]=='noage':
    FB={b:{k:1.0 for k in FB[b]} for b in FB}
D=defaultdict(list)
for r in rows: D[(r['region_code'],r['umd_name'])].append((b(r['by']), float(r['p'])/1e4, int(r['n']), small(r)))
def wmed(xs):
    xs=sorted(xs); tot=sum(w for _,w in xs); c=0
    for v,w in xs:
        c+=w
        if c>=tot/2: return v
def calc(v, sw):
    raw=wmed([(p,n) for _,p,n,_ in v]); fb=dict(FB['lo' if raw<10 else 'hi'])
    q=[p for bk,p,_,s in v if bk=='준신축' and not s]      # 동 실측 비율은 300세대+ 단지로만 잰다
    if MEASURE and len(q)>=2:
        base=st.median(q)
        for bk in ['신축','구축A','구축B']:
            xs=[p for b2,p,_,s in v if b2==bk and not s]
            if len(xs)>=2: lo,hi=CLIP[bk]; fb[bk]=min(hi,max(lo,st.median(xs)/base))
    adj=wmed([(p/fb[bk], n*(sw if s else 1)) for bk,p,n,s in v])
    old=sum(n for bk,_,n,_ in v if bk=='30년+')/sum(n for _,_,n,_ in v)
    q3=[p for bk,p,_,s in v if bk=='준신축' and not s]
    return raw, adj, old, (st.median(q3) if len(q3)>=3 else None)
T=[('최상급지',35),('1급지',25),('2급지',18),('3급지',12),('4급지①',7),('4급지②',0)]
tier=lambda m: next(n for n,c in T if m>=c)
nm=lambda k: REGIONS[k[0]].split(' ',1)[1].replace('시 ',' ')+' '+k[1]
res={}
dropped=[]
for k,v in D.items():
    if len(v)<3: continue
    r0=calc(v,1.0)
    if SMALL_W==0:
        vb=[x for x in v if not x[3]]
        if len(vb)<3: dropped.append((k,r0[1])); continue
        r1=calc(vb,1.0)
    else: r1=calc(v,SMALL_W)
    big=sum(1 for *_,s in v if not s)
    res[k]=dict(raw=r0[0], before=r0[1], after=r1[1], old=r1[2], q3=r1[3], nbig=big, nc=len(v), smallshare=sum(n for *_,n,s in v if s)/sum(n for *_,n,_ in v))
print(f"소단지 가중치 {SMALL_W}, 동 {len(res)}개, 300세대+ 단지 3곳 미만이라 빠진 동 {len(dropped)}개")
for name,c in T:
    sel=sorted([(k,r) for k,r in res.items() if tier(r['after'])==name], key=lambda x:-x[1]['after'])
    cnt=Counter({'11':'서울','41':'경기','28':'인천'}[k[0][:2]] for k,_ in sel)
    print(f"\n[{name}] {len(sel)}동 {dict(cnt)}")
    print("  ", ", ".join(f"{nm(k)} {r['after']:.1f}{'*' if r['old']>=0.5 else ''}" for k,r in sel[:20]))
ch=[(k,r) for k,r in res.items() if tier(r['before'])!=tier(r['after'])]
up=[x for x in ch if x[1]['after']>x[1]['before']]; dn=[x for x in ch if x[1]['after']<x[1]['before']]
print(f"\n가중 전→후 급지 바뀐 동 {len(ch)} (올라감 {len(up)}, 내려감 {len(dn)})")
for lab,xs in (('올라감',up),('내려감',dn)):
    xs=sorted(xs,key=lambda x:-abs(x[1]['after']-x[1]['before']))[:12]
    print(' ',lab, "; ".join(f"{nm(k)} {r['before']:.1f}→{r['after']:.1f} ({tier(r['before'])}→{tier(r['after'])}, 소단지 거래 {r['smallshare']:.0%})" for k,r in xs))
print("\n대형 단지(300+) 1곳 이하인 동", sum(1 for r in res.values() if r['nbig']<=1))
flag=[(k,r) for k,r in res.items() if r['q3'] is not None and tier(r['q3'])!=tier(r['after'])]
print("확인 필요(300+ 준신축 3곳+ 값과 급지 다름)", len(flag), "; ".join(f"{nm(k)} {r['after']:.1f}/{r['q3']:.1f}" for k,r in sorted(flag,key=lambda x:-x[1]['after'])[:10]))
print("재건축 기대 동", sum(1 for r in res.values() if r['old']>=0.5))
for k in [('11710','잠실동'),('11740','둔촌동'),('11740','고덕동'),('11740','상일동'),('41450','망월동'),('41450','선동'),('41450','풍산동'),('41360','다산동'),('11740','암사동'),('11740','천호동'),('11740','명일동')]:
    if k in res: r=res[k]; print(f"  {nm(k):12} 실거래 {r['raw']:.1f} | 가중 전 {r['before']:.1f}({tier(r['before'])}) → 후 {r['after']:.1f}({tier(r['after'])}) 소단지 거래 {r['smallshare']:.0%}")
if dropped:
    dc=Counter(tier(a) for _,a in dropped); print("빠진 동의 가중 전 급지", dict(dc)); print("  큰 곳:", ", ".join(f"{nm(k)} {a:.1f}" for k,a in sorted(dropped,key=lambda x:-x[1])[:15]))
json.dump({f"{k[0]}|{k[1]}":r for k,r in res.items()}, open(os.environ.get('E1_DIR','/tmp/e1')+'/e1_res.json','w'), ensure_ascii=False)
