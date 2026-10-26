"""template_v2.html + out/data.json → out/house-check-v2.html (화면 흐름 재구성 시안, 탭 4개 + 단지 상세).

기존 시안(build.py → house-check-screens.html)은 그대로 두고 비교용으로 따로 만든다(2026-10-20 사용자 결정).
E6 분기 시계열은 단지 일련번호 → 시계열 사전(v2_e6)으로 바꿔 넣는다.

    python tools/prototype/extract.py && python tools/prototype/compute.py && python tools/prototype/build_v2.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "out/data.json").read_text(encoding="utf-8"))
e6 = d.pop("e6", None) or {}
qs = e6.get("q", [])
# 단지 → 분기 중앙가 20분기(1층 제외 중개). 84 는 E6 와 같고, 59 도 같은 방법. 4분기 이상 값이 있는 단지만
def _aligned(raw):
    out = {}
    for a, v in (raw or {}).items():
        arr = [round(v[q]) if q in v else None for q in qs]
        if sum(x is not None for x in arr) >= 4:
            out[a] = arr
    return out
d["v2_e6"] = {"q": qs, "s": _aligned(d.pop("v2_q84", None)), "s59": _aligned(d.pop("v2_q59", None))}
# 2026-10-25 크기 줄이기: 후보 행의 이름·동은 v2_info 에 있으면 비우고(화면이 채움), 참·거짓은 1·0, 갈아타기 목표 이름도 v2_info 에 있으면 비움
_info = d.get("v2_info", {})
d["cand"] = [[None if (k in (0, 2) and r[23] in _info) else (1 if v is True else 0 if v is False else v) for k, v in enumerate(r)] for r in d.get("cand", [])]
d["v2_e6t"] = [r[:5] + [None if r[1] in _info else r[5]] for r in d.get("v2_e6t", [])]
tmpl = (HERE / "template_v2.html").read_text(encoding="utf-8")
djs = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
html = tmpl.replace("/*DATA*/null", djs)
(HERE / "out/house-check-v2.html").write_text(html, encoding="utf-8")
print(HERE / "out/house-check-v2.html")

# --web <폴더>: 실제 웹(Vercel) 배포 묶음. web/ 의 서버 함수·설정 + index.html(저장 동기화 스크립트를 본문 앞에, 검색 제외)
if "--web" in sys.argv:
    dst = Path(sys.argv[sys.argv.index("--web") + 1])
    web = HERE.parent.parent / "web"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(web, dst, ignore=shutil.ignore_patterns("sync.js", "node_modules"))
    sync = (web / "sync.js").read_text(encoding="utf-8")
    # 2026-10-25 속도: 데이터(약 10MB)를 페이지 안 JS 로 두면 휴대폰에서 첫 화면 8~9초(CPU 4배 느림·10Mbps 시험) →
    # data.json 따로(브라우저가 JSON.parse, 바뀌지 않으면 304) + 화면 코드는 데이터가 온 뒤 실행. 화면은 먼저 '불러오는 중'
    import hashlib
    i = tmpl.index("</style>") + len("</style>")   # 템플릿은 조각(아티팩트가 감쌈) → 웹에서는 문서로 감싼다
    body = tmpl[i:].replace("/*DATA*/null", "window.__D", 1)
    # 2026-10-26 속도 2단계: 템플릿의 /*LATE*/ 앞(공통 도구 + 시장 탭)은 그 부분이 쓰는 데이터(data.json)만 받고 먼저 실행해 첫 화면을 띄우고,
    # 나머지 데이터(data2.json, 약 90%)는 동시에 받기 시작해 오면 D 에 합친 뒤 뒷부분을 실행. 그 전에 다른 탭을 누르면 '불러오는 중'
    import re
    j = body.index("<script>")
    k = body.index("/*LATE*/")
    e = body.index("</script>", k)
    part_a, part_b = body[j + len("<script>"):k], body[k:e]
    core_keys = set(re.findall(r"\bD\.([A-Za-z0-9_]+)", part_a)) | {"asof", "region_names"}
    core = {x: v for x, v in d.items() if x in core_keys}
    late = {x: v for x, v in d.items() if x not in core_keys}
    body = (body[:j] + '<script type="text/plain" id="hc-a">' + part_a + '</script>\n<script type="text/plain" id="hc-b">' + part_b + body[e:])
    djs = json.dumps(core, ensure_ascii=False, separators=(",", ":"))
    djs2 = json.dumps(late, ensure_ascii=False, separators=(",", ":"))
    ver, ver2 = hashlib.md5(djs.encode()).hexdigest()[:10], hashlib.md5(djs2.encode()).hexdigest()[:10]
    run = "function (id) { var s = document.createElement('script'); s.textContent = document.getElementById(id).textContent; document.body.appendChild(s); }"
    loader = ("<div id=\"hc-loading\" style=\"position:fixed;inset:0;display:grid;place-items:center;background:var(--bg);color:var(--ink-2);font-size:15px;z-index:99\">불러오는 중…</div>\n"
              "<style>body:not(.hc-b) .tab-page:not(#home)::before { content: '나머지 데이터를 불러오는 중…'; display: block; padding: 20px 4px; color: var(--ink-3); }"
              " body.hc-fail .tab-page:not(#home)::before { content: '데이터를 불러오지 못했습니다. 새로고침해 주세요.'; }</style>\n"
              "<script>(function () { var run = " + run + ";"
              " var fail = function () { document.body.classList.add('hc-fail'); var l = document.getElementById('hc-loading'); if (l) l.textContent = '데이터를 불러오지 못했습니다. 새로고침해 주세요.'; };"
              " Promise.all([window.__DP, window.__stateP]).then(function (a) { window.__D = a[0]; run('hc-a'); var l = document.getElementById('hc-loading'); if (l) l.remove();"
              " return window.__DP2; }).then(function (late) { Object.assign(window.__D, late); run('hc-b'); document.body.classList.add('hc-b'); }).catch(fail); })();</script>\n")
    page = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta name="robots" content="noindex, nofollow">\n'
            # 2026-10-26 속도: 데이터 받기를 <head> 맨 앞에서 시작(글꼴 CSS·본문 HTML 을 기다리지 않게) → 약 0.4초
            + "<script>window.__DP = fetch('data.json?v=" + ver + "').then(function (r) { return r.json(); });"
            + " window.__DP2 = fetch('data2.json?v=" + ver2 + "').then(function (r) { return r.json(); });</script>\n"
            + tmpl[:i] + (f"\n<script>window.HC_MAPKEY = {json.dumps(os.environ['HC_MAPKEY'])};</script>" if os.environ.get("HC_MAPKEY") else "")
            + f"\n<script>{sync}</script>\n</head>\n<body>\n" + body + "\n" + loader + "</body>\n</html>\n")
    (dst / "index.html").write_text(page, encoding="utf-8")
    (dst / "data.json").write_text(djs, encoding="utf-8")
    (dst / "data2.json").write_text(djs2, encoding="utf-8")
    print(f"  첫 데이터 {len(djs) // 1024:,}KB({len(core)}개 키) · 나머지 {len(djs2) // 1024:,}KB")
    print(dst / "index.html")
