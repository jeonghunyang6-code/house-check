"""심평원 파일 내려받기 함수, 역 후보 제목 재시도 (임시, PR 전에 지운다)."""
import io, csv, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from collector.datagokr_file import _req, download, DownloadError, CaptchaRequired
from jobs.infra import _decode

UA = {"User-Agent": "house-check (personal research)"}
H = "https://opendata.hira.or.kr"


def fetch(u, n=2000000):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            return r.status, r.read(n), dict(r.headers)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), {}


print("### 1. 심평원 fn_fileDown 정의")
for js in ["/js/common.js?t=1", "/js/hira.od.common.js?t=1", "/js/default.js"]:
    st, b, _ = fetch(H + js)
    t = b.decode("utf-8", "replace")
    for m in re.finditer(r"fn_fileDown\s*[=:(]|function\s+fn_fileDown", t):
        print(js, st, re.sub(r"\s+", " ", t[m.start():m.start() + 1200]))
st, b, _ = fetch(H + "/op/opc/selectOpenData.do?sno=11925")
t = b.decode("utf-8", "replace")
for m in re.finditer(r"fileDown", t):
    s = t[max(0, m.start() - 200):m.start() + 400]
    if "function" in s or "url" in s.lower():
        print("  page:", re.sub(r"\s+", " ", s))
print("  forms:", re.findall(r"<form[^>]*>", t)[:5])

print("### 2. 역 후보 제목 (재시도 포함)")
cands = ["15041483", "15109337", "15109338", "15109339", "15109340", "15133918", "15133920", "15133922", "15136814",
         "15152969", "15152970", "15152978", "15159772", "15162006", "15125819", "15125821", "15130544", "15120790", "15043686"]
keep = []
for pk in cands:
    try:
        t = _req(f"https://www.data.go.kr/data/{pk}/fileData.do").decode("utf-8", "replace")
    except DownloadError as e:
        print(pk, "실패", e); continue
    title = (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1].strip()
    print(pk, title[:90], flush=True)
    if re.search(r"역위치|위치정보|좌표", title) and not re.search(r"부산|대구|대전|광주|울산|물품|제세동", title):
        keep.append(pk)
print("### 3. 내려받기:", keep)
for pk in keep[:8]:
    try:
        name, data = download(pk)
    except CaptchaRequired as e:
        print(pk, "보안문자 → 멈춤", e); break
    except DownloadError as e:
        print(pk, "실패", e); continue
    txt = _decode(data)
    rows = list(csv.reader(io.StringIO(txt)))
    print(f"=== {pk} {name} rows={len(rows)} hdr={rows[0][:12] if rows else None}")
    lines = {}
    for r in rows[1:]:
        for c in r:
            if re.search(r"(선|라인|GTX)$", c.strip()) and len(c) < 20:
                lines[c.strip()] = lines.get(c.strip(), 0) + 1
    print("   lines:", sorted(lines.items(), key=lambda x: -x[1])[:40])
    if len(rows) < 1500 and re.search(r"신림|김포|서해|GTX|경춘", txt):
        print(f"<<<CSV {pk}"); print(txt.strip()); print("CSV>>>")
    time.sleep(3)
