"""template_v2.html + out/data.json → out/house-check-v2.html (화면 흐름 재구성 시안, 탭 4개 + 단지 상세).

기존 시안(build.py → house-check-screens.html)은 그대로 두고 비교용으로 따로 만든다(2026-10-20 사용자 결정).
E6 분기 시계열은 단지 일련번호 → 시계열 사전(v2_e6)으로 바꿔 넣는다.

    python tools/prototype/extract.py && python tools/prototype/compute.py && python tools/prototype/build_v2.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "out/data.json").read_text(encoding="utf-8"))
e6 = d.pop("e6", None) or {}
d["v2_e6"] = {"q": e6.get("q", []), "s": {r[4]: r[3] for r in e6.get("cx", []) if len(r) > 4}}   # 단지 일련번호 → 84㎡ 분기 중앙가 20분기
html = (HERE / "template_v2.html").read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
(HERE / "out/house-check-v2.html").write_text(html, encoding="utf-8")
print(HERE / "out/house-check-v2.html")
