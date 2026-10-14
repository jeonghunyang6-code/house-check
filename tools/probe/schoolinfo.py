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
apis = []
for m in re.finditer(r"loadOpenApi\(\s*'?(\w+)'?\s*,\s*'?(\w+)'?\s*\)", t):
    tail = re.sub(r"<[^>]+>", " ", t[m.end():m.end() + 300])
    name = re.sub(r"\s+", " ", tail).strip()[:40]
    apis.append((m.group(1), m.group(2), name))
print("apis:", len(apis))
for a_ in apis:
    print("  ", a_)
for go, grp, name in apis:
    if not re.search(r"학업|성취|진로|진학|졸업", name):
        continue
    page = get("https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l0.do", {"goNo": go, "groupNo": grp})
    tx = text(page)
    i = tx.find("번호 항목명 항목 ID")
    j = tx.find("Sample Url", i + 10)
    print(f"=== {name} goNo={go} group={grp}")
    print("   spec:", tx[i:i + 2500] if i >= 0 else "없음")
    print("   apiType:", sorted(set(re.findall(r"apiType=(\d+)", page)))[:5], re.findall(r'name="apiType"[^>]*value="(\d+)"|value="(\d+)"[^>]*name="apiType"', page)[:3])
print("### 연도별 성공 항목")
for yr in ("2026", "2024"):
    ok = []
    for at in range(1, 80):
        q = urllib.parse.urlencode({"apiKey": KEY, "apiType": at, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03", "pbanYr": yr})
        try:
            d = json.loads(get(f"https://www.schoolinfo.go.kr/openApi.do?{q}"))
        except Exception:
            continue
        if d.get("list"):
            ok.append(at)
    print(yr, ok)
