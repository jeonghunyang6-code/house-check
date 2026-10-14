"""서울 생활권 데이터셋 후보의 제목·파일 확인 (임시)."""
import re, urllib.request

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "house-check (personal research)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def text(b):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", b, flags=re.S)))

for oa in ["OA-15527", "OA-15528", "OA-15529", "OA-15530", "OA-15531", "OA-20286", "OA-21149", "OA-10756", "OA-10760"]:
    st, b = fetch(f"https://data.seoul.go.kr/dataList/{oa}/S/1/datasetView.do")
    t = re.search(r"<title>(.*?)</title>", b, re.S)
    tx = text(b)
    i = tx.find("데이터 설명") if "데이터 설명" in tx else tx.find("설명")
    files = sorted(set(re.findall(r"[\w\-가-힣()_.]+\.(?:zip|shp|csv|xlsx|xls|json|geojson)", b)))[:10]
    print(f"=== {oa} -> {st} {t.group(1).strip()[:80] if t else ''}\n  files={files}\n  {tx[max(0, i):i + 500]}")
for pid in ["15071702/fileData.do", "15071707/fileData.do", "15064078/fileData.do", "15125737/fileData.do", "15134540/fileData.do"]:
    st, b = fetch("https://www.data.go.kr/data/" + pid)
    t = re.search(r"<title>(.*?)</title>", b, re.S)
    tx = text(b)
    i = tx.find("설명")
    print(f"=== {pid} -> {st} {t.group(1).strip()[:80] if t else ''}\n  {tx[max(0, i):i + 400]}")
