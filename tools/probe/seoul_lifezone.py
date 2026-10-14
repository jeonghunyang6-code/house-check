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

st, page, _ = fetch("https://data.seoul.go.kr/dataList/OA-15527/S/1/datasetView.do")
page = page.decode("utf-8", "replace")
m = re.search(r"function downloadFile\s*\(.*?\{(.*?)\n\s*\}", page, re.S)
print("downloadFile body:", re.sub(r"\s+", " ", m.group(1))[:900] if m else None)

for oa, seq in [("OA-15527", "4"), ("OA-15531", None), ("OA-15528", None)]:
    if seq is None:
        _, pg, _ = fetch(f"https://data.seoul.go.kr/dataList/{oa}/S/1/datasetView.do")
        mm = re.search(rb"downloadFile\('(\d+)'\)", pg)
        seq = mm.group(1).decode() if mm else "1"
    for data in [{"infId": oa, "seqNo": seq, "seq": seq, "infSeq": "1"}, {"infId": oa, "seqNo": seq}]:
        st, b, h = fetch("https://data.seoul.go.kr/dataList/down2api.do", urllib.parse.urlencode(data).encode())
        print(f"=== {oa} seq={seq} {list(data)} -> {st} {h.get('Content-Type')} {h.get('Content-Disposition')} len={len(b)}")
        if b[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(b))
            print("  zip:", [(i.filename.encode('cp437').decode('cp949', 'replace'), i.file_size) for i in z.infolist()])
            for i in z.infolist():
                if i.filename.lower().endswith(".dbf"):
                    n, f, rows = dbf(z.read(i))
                    print("  dbf", n, "records, fields", f)
                    for r in rows:
                        print("   ", r)
            break
        else:
            print("  body:", b[:300])
