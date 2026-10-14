"""중학교 학교군 SHP·학구도 연계정보·학교위치 파일 구조 확인 (임시, PR 전에 지운다)."""
import csv, io, sys, zipfile
sys.path.insert(0, ".")
from collector.datagokr_file import download
from jobs.infra import _decode
import shapefile

name, data = download("15159264")
print("=== 15159264", name, len(data))
z = zipfile.ZipFile(io.BytesIO(data))
print(z.namelist())
base = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
prj = [n for n in z.namelist() if n.lower().endswith(".prj")]
if prj:
    print("prj:", z.read(prj[0])[:300])
sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")),
                      shx=io.BytesIO(z.read(base + ".shx")), encoding="cp949")
print("fields:", [f[0] for f in sf.fields[1:]], "n=", len(sf))
for r in [r for r in sf.records() if str(r[list(r.as_dict()).index("SD_CD")] if "SD_CD" in r.as_dict() else "") in ("11", "41")][:6]:
    print("  ", r.as_dict())
for pk in ("15159266", "15159184"):
    name, data = download(pk)
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data)); print(pk, z.namelist())
        data = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv")))
    txt = _decode(data)
    rows = list(csv.DictReader(io.StringIO(txt)))
    print(f"=== {pk} {name} rows={len(rows)} cols={list(rows[0])}")
    for r in [r for r in rows if any("대치" in str(v) or "대청" in str(v) for v in r.values())][:6]:
        print("  ", r)
