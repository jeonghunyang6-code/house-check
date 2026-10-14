"""학교알리미 공개용 데이터(파일) 목록·내려받기 방식 확인 (임시, PR 전에 지운다)."""
import re, urllib.parse, urllib.request

UA = {"User-Agent": "house-check (personal research)"}


def get(u, data=None, n=3000000):
    body = urllib.parse.urlencode(data).encode() if data else None
    with urllib.request.urlopen(urllib.request.Request(u, data=body, headers=UA), timeout=90) as r:
        raw, ct = r.read(n), r.headers.get("Content-Type", "")
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc), ct, raw
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace"), ct, raw


t, ct, _ = get("https://www.schoolinfo.go.kr/ng/go/pnnggo_a01_l2.do")
txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)))
i = txt.find("공개용")
print("text:", txt[i:i + 3000])
for m in re.finditer(r'on[cC]lick="([^"]{0,200})"', t):
    if re.search(r"[Dd]own|file|excel|xls", m.group(1)):
        print("click:", m.group(1))
for m in re.finditer(r"function\s+(\w*[Dd]own\w*)\s*\(([^)]*)\)\s*\{(.{0,600})", t, re.S):
    print("fn:", m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3)))
print("selects:", re.findall(r'<select[^>]*(?:id|name)="([^"]+)"', t))
for sel in re.findall(r'<select[^>]*(?:id|name)="([^"]+)"[^>]*>(.*?)</select>', t, re.S):
    print("  opt", sel[0], re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', sel[1])[:40])
