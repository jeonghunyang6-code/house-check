"""학교알리미 OpenAPI 종류·응답 구조 확인 (임시, PR 전에 지운다). 키는 SCHOOLINFO_API_KEY 환경 변수, 출력하지 않는다."""
import json, os, re, urllib.parse, urllib.request

UA = {"User-Agent": "house-check (personal research)"}
KEY = os.environ.get("SCHOOLINFO_API_KEY", "")
print("키 있음:", bool(KEY))


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


t = get("https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do")
links = sorted(set(re.findall(r"pnnggo_a01_l\d+\.do[^\"'<> ]*", t)))
print("links:", links[:80])
for m in re.finditer(r"apiType[^0-9]{0,40}(\d+)", t):
    print("  apiType ctx:", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, m.start() - 200):m.end() + 50])))
# 안내 페이지의 메뉴 항목 (이름 ↔ 링크)
for m in re.finditer(r'<a[^>]+href="([^"]*pnnggo[^"]*)"[^>]*>(.*?)</a>', t, re.S):
    print("  menu:", m.group(1)[:80], re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()[:40])

print("### 호출 시험 (서울 강남구 중학교)")
for at in list(range(0, 80)):
    q = urllib.parse.urlencode({"apiKey": KEY, "apiType": at, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03"})
    try:
        body = get(f"https://www.schoolinfo.go.kr/openApi.do?{q}")
    except Exception as e:
        print(at, "ERR", type(e).__name__, e); continue
    body = body.replace(KEY, "***") if KEY else body
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        print(at, "non-json", body[:150].replace("\n", " ")); continue
    lst = d.get("list") if isinstance(d, dict) else None
    if lst:
        print(at, d.get("resultCode"), d.get("resultMsg"), "rows", len(lst), "keys", list(lst[0])[:40])
        print("    first:", json.dumps(lst[0], ensure_ascii=False)[:600])
    else:
        print(at, json.dumps(d, ensure_ascii=False)[:200])
