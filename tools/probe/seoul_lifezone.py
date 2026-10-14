"""서울 생활권경계(OA-15527 등) 내려받기·DBF 속성 확인 (임시)."""
import io, re, struct, urllib.parse, urllib.request, zipfile

UA = {"User-Agent": "house-check (personal research)", "Referer": "https://data.seoul.go.kr/"}

def fetch(u, data=None):
    try:
        req = urllib.request.Request(u, data=data, headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read(), dict(r.headers)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), {}

def dbf(b, n=8):
    nrec, hlen, rlen = struct.unpack("<IHH", b[4:12])
    fields, p = [], 32
    while b[p] != 0x0D:
        name = b[p:p + 11].split(b"\0")[0].decode("ascii", "replace")
        fields.append((name, b[p + 16]))
        p += 32
    rows = []
    for i in range(min(n, nrec)):
        rec = b[hlen + i * rlen + 1: hlen + (i + 1) * rlen]
        out, q = [], 0
        for name, ln in fields:
            out.append(rec[q:q + ln].decode("cp949", "replace").strip())
            q += ln
        rows.append(out)
    return nrec, [f for f, _ in fields], rows

for oa in ["OA-15527"]:
    _, page, _ = fetch(f"https://data.seoul.go.kr/dataList/{oa}/S/1/datasetView.do")
    page = page.decode("utf-8", "replace")
    form = re.search(r'<form[^>]*name="frmFile".*?</form>', page, re.S)
    fields = dict(re.findall(r'<input[^>]*name="(\w+)"[^>]*value="([^"]*)"', form.group(0))) if form else {}
    seq = re.search(r"downloadFile\('(\d+)'\)", page).group(1)
    fields["seq"] = seq
    print("form fields:", fields)
    st, b, h = fetch("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false", urllib.parse.urlencode(fields).encode())
    print(f"=== {oa} -> {st} {h.get('Content-Type')} len={len(b)} head={b[:4]}")
    if b[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(b))
        print("  zip:", [(i.filename.encode('cp437').decode('cp949', 'replace'), i.file_size) for i in z.infolist()])
        for i in z.infolist():
            if i.filename.lower().endswith(".dbf"):
                n, f, rows = dbf(z.read(i), 200)
                print("  dbf", n, "records, fields", f)
                for r in rows:
                    print("   ", r)
            if i.filename.lower().endswith(".prj"):
                print("  prj:", z.read(i)[:300])
    else:
        print("  body:", b[:400])
