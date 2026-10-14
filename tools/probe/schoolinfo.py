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
# API 목록에서 이름과 번호(onclick 인자 등)
for m in re.finditer(r'<a[^>]*(?:onclick|href)="([^"]*)"[^>]*>\s*([^<]{2,40})</a>', t):
    if re.search(r"\d", m.group(1)) and ("fn" in m.group(1) or "apiType" in m.group(1) or "javascript" in m.group(1)):
        print("item:", m.group(2).strip(), "|", m.group(1)[:100])
forms = re.findall(r"<form[^>]*>", t)
print("forms:", forms[:5])
for m in re.finditer(r"function\s+(\w+)\s*\(([^)]*)\)\s*\{(.{0,400})", t, re.S):
    if any(k in m.group(1).lower() for k in ("api", "detail", "view", "sel", "move")):
        print("fn:", m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3))[:300])
i = text(t).find("항목 ID")
print("spec0:", text(t)[i - 200:i + 1500] if i >= 0 else "없음")

print("### depthNo 필요한 항목")
for at in (27, 28, 35, 58):
    for depth in ("1", "2", "3"):
        q = urllib.parse.urlencode({"apiKey": KEY, "apiType": at, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03",
                                    "pbanYr": "2025", "depthNo": depth})
        body = get(f"https://www.schoolinfo.go.kr/openApi.do?{q}").replace(KEY, "***")
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            print(at, depth, body[:120]); continue
        lst = d.get("list")
        if lst:
            print(at, depth, "rows", len(lst), json.dumps(lst[0], ensure_ascii=False)[:900])
        else:
            print(at, depth, json.dumps(d, ensure_ascii=False)[:160])
print("### 51 첫 행 전체")
q = urllib.parse.urlencode({"apiKey": KEY, "apiType": 51, "sidoCode": "11", "sggCode": "11680", "schulKndCode": "03", "pbanYr": "2025"})
d = json.loads(get(f"https://www.schoolinfo.go.kr/openApi.do?{q}"))
for r in d["list"][:24]:
    if r.get("SCHUL_NM") in ("대청중학교", "대명중학교", "단국대학교사범대학부속중학교", "개원중학교"):
        print(json.dumps({k: v for k, v in r.items() if not k.startswith(("ADR", "USER", "SCHUL_RD", "HMPG", "ZIP", "DTLAD", "ATPT", "JU_", "LCTN", "FO", "PERC"))}, ensure_ascii=False))
