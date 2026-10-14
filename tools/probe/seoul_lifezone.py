"""서울 생활권경계(OA-15527) 내려받기 방법·내용 확인 (임시)."""
import io, re, urllib.parse, urllib.request, zipfile, struct

UA = {"User-Agent": "house-check (personal research)"}

def fetch(u, data=None, raw=False):
    try:
        req = urllib.request.Request(u, data=data, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            return r.status, (b if raw else b.decode("utf-8", "replace")), dict(r.headers)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", {}

st, b, _ = fetch("https://data.seoul.go.kr/dataList/OA-15527/S/1/datasetView.do")
for m in re.finditer(r"UPIS_SHP_ZON100", b):
    print("CTX:", re.sub(r"\s+", " ", b[max(0, m.start() - 600):m.start() + 300]))
    break
print("funcs:", sorted(set(re.findall(r"(fn\w*[Dd]own\w*|download\w*)\s*\(([^)]{0,120})\)", b)))[:20])
print("urls:", sorted(set(re.findall(r"['\"](/[\w/]*[Dd]own[\w/.]*)['\"]", b)))[:20])
