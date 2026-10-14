"""SGIS(통계청) 접속·응답 형식 확인 (임시). 키·토큰은 출력하지 않는다."""
import json, os, urllib.parse, urllib.request
CK, CS = os.environ.get("SGIS_CONSUMER_KEY", ""), os.environ.get("SGIS_CONSUMER_SECRET", "")
print("keys:", bool(CK), bool(CS))
B = "https://sgisapi.kostat.go.kr/OpenAPI3"
SECRETS = [x for x in (CK, CS) if x]

def get(path, **p):
    try:
        with urllib.request.urlopen(B + path + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            t = r.read().decode("utf-8", "replace")
    except Exception as e:
        t = f"ERR {type(e).__name__}: {e}"
    for s in SECRETS + [p.get("accessToken", "")]:
        if s:
            t = t.replace(s, "***")
    return t

a = get("/auth/authentication.json", consumer_key=CK, consumer_secret=CS)
try:
    tok = json.loads(a)["result"]["accessToken"]
except Exception:
    tok = None
print("auth:", a if not tok else "ok (token hidden)")
if tok:
    for addr in ("서울특별시 송파구 송파대로 345", "서울특별시 송파구 가락동 913"):
        print("geocodewgs84", addr, get("/addr/geocodewgs84.json", accessToken=tok, address=addr, resultcount=1)[:900])
        print("geocode(UTM-K)", addr, get("/addr/geocode.json", accessToken=tok, address=addr, resultcount=1)[:600])
    b = get("/boundary/hadmarea.geojson", accessToken=tok, year="2024", adm_cd="11240", low_search="1")
    try:
        j = json.loads(b)
        fs = j.get("features") or []
        print("boundary 송파 하위:", len(fs), "개", [f["properties"] for f in fs[:3]], "geom type", fs[0]["geometry"]["type"] if fs else None, "len", len(b))
    except Exception:
        print("boundary:", b[:600])
    print("stage:", get("/addr/stage.json", accessToken=tok, cd="11240")[:600])
