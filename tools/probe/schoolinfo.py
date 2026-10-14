"""학교알리미 OpenAPI 종류·응답 구조 확인 (임시, PR 전에 지운다). 키는 SCHOOLINFO_API_KEY 환경 변수, 출력하지 않는다."""
import json, os, re, urllib.parse, urllib.request

UA = {"User-Agent": "house-check (personal research)"}
KEY = os.environ.get("SCHOOLINFO_API_KEY", "")
print("키 있음:", bool(KEY))


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


COMMON = {"DGHT_SC_CODE","FOND_SC_CODE","SCHUL_RDNZC","USER_TELNO_GA","FOND_YMD","LGTUD","SCHUL_CRSE_SC_VALUE","SCHUL_RDNDA","SCHUL_FOND_TYP_CODE","SHL_IDF_CD","SCHUL_RDNMA","FOAS_MEMRD","BNHH_YN","ATPT_OFCDC_ORG_NM","ABSCH_YN","HMPG_ADRES","LTTUD","ATPT_OFCDC_ORG_CODE","LCTN_SC_CODE","ADRCD_CD","ADRCD_ID","SCHUL_CRSE_SC_VALUE_NM","JU_ORG_NM","COEDU_SC_CODE","PERC_FAXNO","DTLAD_BRKDN","ADRCD_NM","SCHUL_KND_SC_CODE","USER_TELNO","JU_ORG_CODE","CLOSE_YN","ZIP_CODE","ADRES_BRKDN","USER_TELNO_SW","SCHUL_NM"}
print("### 호출 시험 (서울 강남구 중학교)")
for at in list(range(1, 80)):
    q = urllib.parse.urlencode({"apiKey": KEY, "apiType": at, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03", "pbanYr": "2025"})
    try:
        body = get(f"https://www.schoolinfo.go.kr/openApi.do?{q}")
    except Exception as e:
        print(at, "ERR", type(e).__name__, e); continue
    body = body.replace(KEY, "***") if KEY else body
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        print(at, "non-json", body[:150].replace("\n", " ")); continue
    lst = d.get("list") if isinstance(d, dict) else None
    if lst:
        print(at, "rows", len(lst), "keys", [k for k in lst[0] if k not in COMMON][:45])
        print("    first:", json.dumps({k: v for k, v in lst[0].items() if k not in COMMON or k == "SCHUL_NM"}, ensure_ascii=False)[:700])
    else:
        print(at, json.dumps(d, ensure_ascii=False)[:200])
