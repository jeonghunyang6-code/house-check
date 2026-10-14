"""서울도시공간포털 지역생활권 페이지 구조 확인 (임시). 공개 페이지 몇 장만 읽는다."""
import re, urllib.request

def fetch(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "house-check (personal research)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

for u in ["https://urban.seoul.go.kr/view/html/PMNU3040000001", "https://urban.seoul.go.kr/view/html/PMNU2030000000"]:
    st, b = fetch(u)
    print(f"=== {u} -> {st} len={len(b)}")
    t = re.search(r"<title>(.*?)</title>", b, re.S)
    print("title:", t.group(1).strip() if t else None)
    links = sorted(set(re.findall(r'href="([^"]+)"', b)))
    print("links with 생활권/PMNU304/download:", [l for l in links if re.search(r"PMNU304|PMNU203|download|\.zip|\.shp|\.xlsx|\.csv|\.pdf", l)][:60])
    text = re.sub(r"<[^>]+>", " ", b)
    text = re.sub(r"\s+", " ", text)
    i = text.find("생활권")
    print("text:", text[max(0, i - 200):i + 1500])
    js = sorted(set(re.findall(r'(?:url|ajax|action)\s*[:=]\s*["\']([^"\']+)["\']', b)))
    print("ajax/url:", js[:40])
