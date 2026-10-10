"""WebVTT 자막을 (시작초, 텍스트) 목록으로 변환한다.

유튜브 자동 자막은 같은 문장이 다음 큐에 다시 나오는 롤링 방식이라,
직전 텍스트와 겹치는 부분을 잘라내 중복을 없앤다.
"""

from __future__ import annotations

import re

_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})\.(\d{3})\s+-->")
_TAG = re.compile(r"<[^>]+>")


def _seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(text: str) -> list[dict]:
    segments: list[dict] = []
    seen_lines: list[str] = []
    start: float | None = None

    for raw in text.splitlines():
        line = raw.strip()
        m = _TIME.match(line)
        if m:
            start = _seconds(*m.groups())
            continue
        if start is None or not line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        clean = _TAG.sub("", line).strip()
        if not clean or clean in seen_lines[-3:]:
            continue
        seen_lines.append(clean)
        segments.append({"t": round(start, 1), "text": clean})
    return segments
