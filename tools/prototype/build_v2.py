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
