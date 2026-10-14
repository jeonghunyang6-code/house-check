"""빠진 지하철 노선 후보 파일·병원(심평원) 내려받기 방식·학원(나이스) 한도 확인 (임시, PR 전에 지운다)."""
import io, csv, json, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, ".")
from collector.datagokr_file import download, DownloadError, CaptchaRequired
from jobs.infra import _decode

UA = {"User-Agent": "house-check (personal research)"}


def fetch(u, n=800000, data=None):
    try:
        body = urllib.parse.urlencode(data).encode() if data else None
        with urllib.request.urlopen(urllib.request.Request(u, data=body, headers=UA), timeout=60) as r:
            return r.status, r.read(n)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()


print("### 1. 후보 데이터 제목")
cands = ["15041483", "15109337", "15109338", "15109339", "15109340", "15133918", "15133920", "15133922", "15136814",
         "15152969", "15152970", "15152978", "15159772", "15162006", "15125819", "15125821", "15130544", "15120790",
         "15043686", "15036905", "15085669", "15041234"]
keep = []
for pk in cands:
    st, b = fetch(f"https://www.data.go.kr/data/{pk}/fileData.do")
    t = b.decode("utf-8", "replace")
    title = (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1].strip()
    print(pk, st, title[:90])
    if re.search(r"역위치|역사.*(좌표|위치)|위치정보|좌표", title) and not re.search(r"부산|대구|대전|광주|울산|물품|제세동", title):
        keep.append(pk)
    time.sleep(1)

print("### 2. 내려받기:", keep)
for pk in keep:
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
            if re.search(r"(선|라인|GTX|철도)$", c.strip()):
                lines[c.strip()] = lines.get(c.strip(), 0) + 1
    print("   lines:", sorted(lines.items(), key=lambda x: -x[1])[:30])
    if len(rows) < 2500:
        print(f"<<<CSV {pk}"); print(txt.strip()); print("CSV>>>")
    time.sleep(3)

print("### 3. 심평원 fn_fileDown")
st, b = fetch("https://opendata.hira.or.kr/op/opc/selectOpenData.do?sno=11925")
t = b.decode("utf-8", "replace")
i = t.find("function fn_fileDown")
print(st, re.sub(r"\s+", " ", t[i:i + 1500]) if i >= 0 else "함수 정의 없음")
for m in re.finditer(r"fn_fileDown\('326801'\)", t):
    print("  ctx:", re.sub(r"<[^>]+>|\s+", " ", t[max(0, m.start() - 600):m.start() + 100])[-400:])
for src in sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', t))):
    print("  js:", src)

print("### 4. 나이스 키 없이 한 번에 몇 건")
for ps in (5, 100, 1000):
    st, b = fetch(f"https://open.neis.go.kr/hub/acaInsTiInfo?Type=json&pIndex=1&pSize={ps}&ATPT_OFCDC_SC_CODE=B10", 3000000)
    try:
        d = json.loads(b)
        rows = d["acaInsTiInfo"][1]["row"]
        print(ps, st, len(rows))
    except Exception:
        print(ps, st, b[:300].decode("utf-8", "replace"))
st, b = fetch("https://open.neis.go.kr/hub/acaInsTiInfo?Type=json&pIndex=2&pSize=1000&ATPT_OFCDC_SC_CODE=B10", 3000000)
print("page2", st, b[:200].decode("utf-8", "replace"))
