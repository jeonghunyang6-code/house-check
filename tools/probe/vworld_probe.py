"""위치 데이터 출처 접속 확인 (임시). 키는 출력하지 않는다."""
import re, urllib.request

def fetch(url, n=200000):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "house-check-probe"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(n).decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

for u in ["https://api.vworld.kr/", "https://sgisapi.kostat.go.kr/", "https://business.juso.go.kr/", "https://dapi.kakao.com/",
          "https://openapi.kric.go.kr/", "https://raw.githubusercontent.com/vuski/admdongkor/master/README.md", "https://www.data.go.kr/"]:
    st, b = fetch(u, 300)
    print(f"[host] {u} -> {st} {'' if st else b[:120]}")

# 데이터 상세 페이지에서 항목 이름 확인 (좌표 필드가 있는지)
for pid in ["15106817/openapi.do", "15127532/fileData.do", "15041150/fileData.do", "15012349/fileData.do"]:
    st, b = fetch("https://www.data.go.kr/data/" + pid)
    title = re.search(r"<title>(.*?)</title>", b, re.S)
    hits = sorted(set(re.findall(r"[가-힣A-Za-z_]*(?:위도|경도|좌표|lat|lng|lon|xpos|ypos|[XY]좌표)[가-힣A-Za-z_]*", b)))[:20]
    print(f"[page] {pid} -> {st} {title.group(1).strip()[:80] if title else ''} | {hits}")
