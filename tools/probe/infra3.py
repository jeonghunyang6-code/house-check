"""대형마트(localdata)·병원(HIRA)·학원(NEIS) 출처 접속·내려받기 방법 확인 (임시)."""
import re, urllib.request
UA = {"User-Agent": "house-check (personal research)"}
def fetch(u, n=400000):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
            return r.status, r.read(n), dict(r.headers)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), {}
for u in ["https://file.localdata.go.kr/file/large_scale_retail_stores/info",
          "https://opendata.hira.or.kr/op/opc/selectOpenData.do?sno=11925",
          "https://open.neis.go.kr/portal/data/service/selectServicePage.do?infId=OPEN19220231012134453534385&infSeq=1"]:
    st, b, h = fetch(u)
    t = b.decode("utf-8", "replace")
    print(f"=== {u} -> {st} {h.get('Content-Type')} len={len(b)}")
    print("  title:", (re.search(r"<title>(.*?)</title>", t, re.S) or [None, None])[1])
    for pat in [r"download[^\"'<>]{0,120}", r"\.csv[^\"'<>]{0,60}", r"\.zip[^\"'<>]{0,60}", r"fileDown[^\"'<>]{0,120}", r"fn_\w*[Dd]own\w*\([^)]{0,120}\)"]:
        hits = sorted(set(re.findall(pat, t)))[:6]
        if hits: print("  ", pat[:20], hits)
