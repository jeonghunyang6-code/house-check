"""서울 지역생활권(116개) 행정동 목록이 공개 데이터로 있는지 확인 (임시). 검색 페이지 몇 장만 읽는다."""
import re, urllib.parse, urllib.request

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "house-check (personal research)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def text(b):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", b, flags=re.S)))

for q in ["생활권", "지역생활권", "생활권계획"]:
    for u in [f"https://data.seoul.go.kr/dataList/datasetList.do?searchValue={urllib.parse.quote(q)}",
              f"https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword={urllib.parse.quote(q)}"]:
        st, b = fetch(u)
        t = text(b)
        hits = sorted(set(re.findall(r"[^ ]{0,40}생활권[^ ]{0,40}", t)))[:40]
        ids = sorted(set(re.findall(r"(OA-\d+|/data/\d{7,8}/\w+\.do)", b)))[:40]
        print(f"=== {q} {u.split('/')[2]} -> {st} len={len(b)}\n hits={hits}\n ids={ids}")
