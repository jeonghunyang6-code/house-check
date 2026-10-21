"""template_v2.html + out/data.json → out/house-check-v2.html (화면 흐름 재구성 시안, 탭 4개 + 단지 상세).

기존 시안(build.py → house-check-screens.html)은 그대로 두고 비교용으로 따로 만든다(2026-10-20 사용자 결정).
E6 분기 시계열은 단지 일련번호 → 시계열 사전(v2_e6)으로 바꿔 넣는다.

    python tools/prototype/extract.py && python tools/prototype/compute.py && python tools/prototype/build_v2.py
"""
import json
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
html = (HERE / "template_v2.html").read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
(HERE / "out/house-check-v2.html").write_text(html, encoding="utf-8")
print(HERE / "out/house-check-v2.html")

# --web <폴더>: 실제 웹(Vercel) 배포 묶음. web/ 의 서버 함수·설정 + index.html(저장 동기화 스크립트를 본문 앞에, 검색 제외)
if "--web" in sys.argv:
    dst = Path(sys.argv[sys.argv.index("--web") + 1])
    web = HERE.parent.parent / "web"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(web, dst, ignore=shutil.ignore_patterns("sync.js", "node_modules"))
    sync = (web / "sync.js").read_text(encoding="utf-8")
    i = html.index("</style>") + len("</style>")   # 템플릿은 조각(아티팩트가 감쌈) → 웹에서는 문서로 감싼다
    page = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta name="robots" content="noindex, nofollow">\n'
            + html[:i] + f"\n<script>{sync}</script>\n</head>\n<body>\n" + html[i:] + "\n</body>\n</html>\n")
    (dst / "index.html").write_text(page, encoding="utf-8")
    print(dst / "index.html")
