"""인프라 공공데이터 출처 확인 (임시). 검색 페이지·API 몇 번만 부른다. 키는 출력하지 않는다."""
import os, re, urllib.parse, urllib.request, json
K = os.environ.get("DATA_GO_KR_SERVICE_KEY", "")
UA = {"User-Agent": "house-check (personal research)"}

def fetch(u, n=600000):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
            return r.status, r.read(n).decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()

for kw in ["초중등학교위치", "초등학교통학구역", "도시공원정보", "학원교습소", "대규모점포", "역 위치 정보", "지하철역 위경도", "병원정보서비스"]:
    st, b = fetch("https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=" + urllib.parse.quote(kw))
    items = []
    for m in re.finditer(r'href="/data/(\d+)/(\w+)\.do"[^>]*>(.*?)</a>', b, re.S):
        t = clean(m.group(3))
        if t and (m.group(1), t) not in [(i[0], i[2]) for i in items]:
            items.append((m.group(1), m.group(2), t[:70]))
    print(f"=== 검색 '{kw}' -> {st}")
    for i in items[:8]:
        print("   ", i)

STD = {
    "학교위치": "tn_pubr_public_elesch_mskul_lc_api",
    "통학구역": "tn_pubr_public_elesch_ats_api",
    "도시공원": "tn_pubr_public_cty_park_info_api",
    "대규모점포": "tn_pubr_public_lrge_stor_api",
}
for n, ep in STD.items():
    u = f"https://api.data.go.kr/openapi/{ep}?" + urllib.parse.urlencode({"serviceKey": K, "pageNo": 1, "numOfRows": 2, "type": "json"})
    st, b = fetch(u, 3000)
    print(f"=== API {n} {ep} -> {st}\n   {b.replace(K, '***')[:700]}")
