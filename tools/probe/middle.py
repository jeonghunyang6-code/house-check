"""중학교 학교군 후보 제목·학교알리미 API 종류 확인 (임시, PR 전에 지운다)."""
import re, sys, time, urllib.request
sys.path.insert(0, ".")
from collector.datagokr_file import _req, DownloadError

UA = {"User-Agent": "house-check (personal research)"}
print("### 1. 후보 제목")
for pk in ["15159264", "15159263", "15159266", "15159184", "15099519", "15099520", "15099521", "15099522", "15099523",
           "15099525", "15021148", "15021149", "15021151", "15021153", "15021154", "15021158", "15132449", "15133782"]:
    for kind in ("fileData", "openapi", "standard"):
        try:
            t = _req(f"https://www.data.go.kr/data/{pk}/{kind}.do", tries=2).decode("utf-8", "replace")
        except DownloadError:
            continue
        title = (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1].strip()
        if title and "오류" not in title:
            ext = sorted(set(re.findall(r"\b(SHP|CSV|JSON|XML|ZIP|XLSX?)\b", t)))[:5]
            mod = (re.search(r"수정일\s*</th>\s*<td[^>]*>\s*([\d-]+)", t) or [None, ""])[1]
            print(pk, kind, title[:80], ext, mod, flush=True)
            break
    time.sleep(1)

print("### 2. 학교알리미 OpenAPI 안내 페이지")
with urllib.request.urlopen(urllib.request.Request("https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do", headers=UA), timeout=60) as r:
    raw = r.read()
for enc in ("utf-8", "euc-kr", "cp949"):
    try:
        t = raw.decode(enc); break
    except UnicodeDecodeError:
        continue
txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
txt = re.sub(r"<[^>]+>", " ", txt)
txt = re.sub(r"\s+", " ", txt)
for kw in ["apiType", "학업성취", "진학", "졸업생", "진로", "요청 변수", "요청변수", "pbanYr", "schulKndCode", "인증키", "신청"]:
    for m in list(re.finditer(kw, txt))[:3]:
        print(f"[{kw}]", txt[max(0, m.start() - 150):m.start() + 250])
