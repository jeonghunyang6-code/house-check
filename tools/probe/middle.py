"""중학교 학교군 파일·학교알리미 공시 API·학교 위치 표준데이터 확인 (임시, PR 전에 지운다)."""
import re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from collector.datagokr_file import _req, DownloadError

UA = {"User-Agent": "house-check (personal research)"}


def fetch(u, n=600000):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            return r.status, r.read(n)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()


print("### 1. 공공데이터포털 검색")
for kw in ["중학교학교군", "중학교 학교군", "학구도", "중학구", "학교군", "초중등학교위치", "학교 위치 표준데이터"]:
    try:
        t = _req("https://www.data.go.kr/tcs/dss/selectDataSetList.do?" + urllib.parse.urlencode({"keyword": kw, "perPage": 20})).decode("utf-8", "replace")
    except DownloadError as e:
        print(kw, "실패", e); continue
    ids = list(dict.fromkeys(re.findall(r"/data/(\d+)/(?:fileData|openapi|standard)\.do", t)))
    titles = [re.sub(r"<[^>]+>|\s+", " ", m).strip() for m in re.findall(r'<span class="title">(.*?)</span>', t, re.S)]
    print(f"--- {kw}: {ids[:15]}")
    for x in titles[:15]:
        print("    ", x[:90])
    time.sleep(1)

print("### 2. 학교알리미 공개 API 안내")
for u in ["https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do", "https://www.schoolinfo.go.kr/openApi.do",
          "https://www.schoolinfo.go.kr/openApi/openApiGuide.do"]:
    st, b = fetch(u)
    t = b.decode("utf-8", "replace")
    print(f"--- {u} -> {st} len={len(b)} title={(re.search(r'<title>(.*?)</title>', t, re.S) or [None, ''])[1].strip()[:60]}")
    for pat in [r"apiKey[^\"'<>]{0,80}", r"apiType[^\"'<>]{0,80}", r"openApi[\w/]*\.do[^\"'<>]{0,80}", r"인증키[^<]{0,80}"]:
        hits = sorted(set(re.findall(pat, t)))[:8]
        if hits:
            print("   ", pat[:12], hits)
