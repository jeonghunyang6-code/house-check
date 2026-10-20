"""template_v2.html + out/data.json → out/house-check-v2.html (화면 흐름 재구성 시안, 탭 4개 + 단지 상세).

기존 시안(build.py → house-check-screens.html)은 그대로 두고 비교용으로 따로 만든다(2026-10-20 사용자 결정).
v2 는 E6 분기 시계열 전체(e6)를 쓰지 않아 뺀다(단지별 e6t 만 씀).

    python tools/prototype/extract.py && python tools/prototype/compute.py && python tools/prototype/build_v2.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "out/data.json").read_text(encoding="utf-8"))
d.pop("e6", None)
html = (HERE / "template_v2.html").read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
(HERE / "out/house-check-v2.html").write_text(html, encoding="utf-8")
print(HERE / "out/house-check-v2.html")
