"""빠진 지하철 노선 파일 재시도 + 병원(심평원)·학원(나이스) 출처 확인 (임시, PR 전에 지운다)."""
import io, csv, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from collector.datagokr_file import download, DownloadError, CaptchaRequired
from jobs.infra import _decode

UA = {"User-Agent": "house-check (personal research)"}


def fetch(u, n=600000, data=None):
    try:
        body = urllib.parse.urlencode(data).encode() if data else None
        with urllib.request.urlopen(urllib.request.Request(u, data=body, headers=UA), timeout=60) as r:
            return r.status, r.read(n)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()


print("### 1. 역위치 파일 재시도")
for pk in ["15041307", "15041308", "15041309", "15041328", "15041485"]:
    try:
        name, data = download(pk)
    except CaptchaRequired as e:
        print(pk, "보안문자 → 멈춤", e); break
    except DownloadError as e:
        print(pk, "실패", e); continue
    txt = _decode(data)
    print(f"=== {pk} {name} lines={txt.count(chr(10))}")
    if "역위치" in name:
        print(f"<<<CSV {pk}"); print(txt.strip()); print(f"CSV>>>")
    time.sleep(3)

print("### 2. 빠진 노선 검색")
for kw in ["신림선 역", "김포골드라인 역", "서해선 역위치", "GTX 역", "경춘선 역위치", "역사 위치정보 좌표", "도시철도 역사 좌표"]:
    st, b = fetch("https://www.data.go.kr/tcs/dss/selectDataSetList.do?" + urllib.parse.urlencode({"keyword": kw, "dType": "FILE", "perPage": 20}))
    t = b.decode("utf-8", "replace")
    hits = re.findall(r'href="/data/(\d+)/(fileData|standard)\.do"[^>]*>\s*(?:<span[^>]*>[^<]*</span>)?\s*<span class="title">\s*(.*?)\s*</span>', t, re.S)
    if not hits:
        hits = sorted(set(re.findall(r"/data/(\d+)/(fileData|standard)\.do", t)))
    print(f"--- {kw} -> {st} {hits[:20]}")
    for m in re.finditer(r'<span class="title">\s*(.*?)\s*</span>', t, re.S):
        print("    ", re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip()[:80])

print("### 3. 병원 (심평원)")
key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "")
for path in ["B551182/hospInfoServicev2/getHospBasisList", "B551182/hospInfoService1/getHospBasisList1"]:
    q = urllib.parse.urlencode({"serviceKey": key, "pageNo": 1, "numOfRows": 2, "sidoCd": "110000", "_type": "json"}, safe="%")
    st, b = fetch(f"https://apis.data.go.kr/{path}?{q}", 4000)
    t = b.decode("utf-8", "replace").replace(key, "***") if key else b.decode("utf-8", "replace")
    print(f"--- {path} -> {st}\n{t[:1500]}")
st, b = fetch("https://opendata.hira.or.kr/op/opc/selectOpenData.do?sno=11925")
t = b.decode("utf-8", "replace")
print(f"--- hira page -> {st} len={len(b)}")
for pat in [r"fn_\w*[Dd]own\w*\([^)]{0,160}\)", r"onclick=\"[^\"]{0,200}\"", r"/op/opc/\w+\.do", r"atchFileId[^&\"']{0,60}"]:
    print("  ", pat[:20], sorted(set(re.findall(pat, t)))[:12])
for m in re.finditer(r"<script[^>]*>(.*?)</script>", t, re.S):
    s = m.group(1)
    if "down" in s.lower():
        print("  script:", re.sub(r"\s+", " ", s)[:1500])

print("### 4. 학원 (나이스)")
for u in ["https://open.neis.go.kr/hub/acaInsTiInfo?Type=json&pIndex=1&pSize=3&ATPT_OFCDC_SC_CODE=B10",
          "https://open.neis.go.kr/hub/acaInsTiInfo?Type=json&pIndex=1&pSize=3&ATPT_OFCDC_SC_CODE=B10&ADMST_ZONE_NM=%EA%B0%95%EB%82%A8%EA%B5%AC"]:
    st, b = fetch(u, 6000)
    print(f"--- {u} -> {st}\n{b.decode('utf-8','replace')[:2500]}")
