"""임시: 청약홈 분양정보 API 응답 모양 확인 (PR 전에 지운다). 키는 출력하지 않는다."""
import json, os, urllib.parse, urllib.request, sys
sys.path.insert(0, ".")
k = os.environ["DATA_GO_KR_SERVICE_KEY"]
base = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail?"
for area in ("서울", "경기", "인천"):
    q = urllib.parse.urlencode({"page": 1, "perPage": 2, "serviceKey": k, "cond[SUBSCRPT_AREA_CODE_NM::EQ]": area})
    try:
        with urllib.request.urlopen(base + q, timeout=60) as r:
            d = json.load(r)
        print(area, {x: d.get(x) for x in ("currentCount", "matchCount", "totalCount", "page", "perPage")})
        for it in d.get("data", []):
            print("  keys:", sorted(it))
            print("  ", {x: it.get(x) for x in ("HOUSE_MANAGE_NO", "HOUSE_NM", "HSSPLY_ADRES", "TOT_SUPLY_HSHLDCO", "MVN_PREARNGE_YM", "RCRIT_PBLANC_DE", "HOUSE_SECD_NM", "HOUSE_DTL_SECD_NM", "SUBSCRPT_AREA_CODE_NM")})
    except urllib.error.HTTPError as e:
        print(area, "HTTP", e.code, e.read()[:300])
# 오래된 공고까지 있는지: 마지막 페이지
q = urllib.parse.urlencode({"page": 1, "perPage": 1, "serviceKey": k, "cond[SUBSCRPT_AREA_CODE_NM::EQ]": "서울", "cond[RCRIT_PBLANC_DE::LT]": "2021-01-01"})
try:
    with urllib.request.urlopen(base + q, timeout=60) as r:
        d = json.load(r)
    print("서울 2021 이전", d.get("matchCount"), [ {x: it.get(x) for x in ("HOUSE_NM", "RCRIT_PBLANC_DE", "MVN_PREARNGE_YM")} for it in d.get("data", [])])
except urllib.error.HTTPError as e:
    print("old HTTP", e.code, e.read()[:200])
from collector.sgis import Sgis
sg = Sgis()
for a in ("서울특별시 강동구 둔촌동 170-1번지 일대", "경기도 화성시 동탄면 영천리 일원", "인천광역시 서구 불로동 산 128-1번지"):
    try:
        h = sg.geocode(a)
        print("geo", a, h and {x: h.get(x) for x in ("x", "y", "adm_cd", "adm_nm")})
    except Exception as e:
        print("geo err", a, type(e).__name__, str(e)[:100])
