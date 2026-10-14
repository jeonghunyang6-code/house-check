"""VWorld 접속·응답 형식 확인 (임시). 키는 출력하지 않는다."""
import json, os, urllib.parse, urllib.request
K = os.environ["VWORLD_API_KEY"]
DOM = "https://github.com/jeonghunyang6-code/house-check"

def get(url, **p):
    p.update(key=K, domain=DOM)
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace").replace(K, "***")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".replace(K, "***")

tests = [
    ("geocode parcel", "https://api.vworld.kr/req/address", dict(service="address", request="getcoord", version="2.0", crs="epsg:4326",
      type="parcel", format="json", refine="true", simple="false", address="서울특별시 송파구 가락동 913")),
    ("geocode road", "https://api.vworld.kr/req/address", dict(service="address", request="getcoord", version="2.0", crs="epsg:4326",
      type="road", format="json", refine="true", simple="false", address="서울특별시 송파구 송파대로 345")),
    ("search place", "https://api.vworld.kr/req/search", dict(service="search", request="search", version="2.0", crs="epsg:4326",
      size="3", page="1", query="헬리오시티", type="place", format="json")),
    ("data 법정동 LT_C_ADEMD_INFO", "https://api.vworld.kr/req/data", dict(service="data", request="GetFeature", data="LT_C_ADEMD_INFO",
      size="2", page="1", geometry="false", attribute="true", crs="EPSG:4326", format="json", attrFilter="emd_cd:=:11710107")),
    ("search 지하철역", "https://api.vworld.kr/req/search", dict(service="search", request="search", version="2.0", crs="epsg:4326",
      size="5", page="1", query="잠실역", type="place", category="", format="json")),
]
for name, url, p in tests:
    st, body = get(url, **p)
    print(f"=== {name}: HTTP {st}\n{body[:1500]}\n")
