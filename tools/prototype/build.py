"""template.html + out/data.json → out/house-check-screens.html (화면 시안 한 파일).

    python tools/prototype/extract.py && python tools/prototype/compute.py && python tools/prototype/build.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/null", (HERE / "out/data.json").read_text(encoding="utf-8"))
(HERE / "out/house-check-screens.html").write_text(html, encoding="utf-8")
print(HERE / "out/house-check-screens.html")
