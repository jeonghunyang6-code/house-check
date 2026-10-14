"""학교알리미 API 항목 정의·depthNo 항목 확인 (임시, PR 전에 지운다). 키는 출력하지 않는다."""
import json, os, re, urllib.parse, urllib.request

UA = {"User-Agent": "house-check (personal research)"}
KEY = os.environ.get("SCHOOLINFO_API_KEY", "")


def get(u, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    with urllib.request.urlopen(urllib.request.Request(u, data=body, headers=UA), timeout=60) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def text(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


t = get("https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do")
for m in re.finditer(r"(\$\.ajax|\$\.post|url\s*:)", t):
    print("ajax:", re.sub(r"\s+", " ", t[max(0, m.start() - 100):m.start() + 500]))
for m in re.finditer(r"loadOpenApi\(([^)]*)\)[^<]{0,10}</?[^>]*>?\s*([^<]{0,40})", t):
    print("api:", m.group(1), m.group(2).strip())
print("### depthNo 필요한 항목")
for at in (27, 28):
    for depth, depth2 in (("1", "1"), ("2", "1"), ("3", "1"), ("3", "2"), ("1", "2")):
        q = urllib.parse.urlencode({"apiKey": KEY, "apiType": at, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03",
                                    "pbanYr": "2025", "depthNo": depth, "depthNo2": depth2})
        body = get(f"https://www.schoolinfo.go.kr/openApi.do?{q}").replace(KEY, "***")
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            print(at, depth, depth2, body[:120]); continue
        lst = d.get("list")
        if lst:
            print(at, depth, depth2, "rows", len(lst), json.dumps(lst[0], ensure_ascii=False)[:900])
        else:
            print(at, depth, depth2, json.dumps(d, ensure_ascii=False)[:160])
