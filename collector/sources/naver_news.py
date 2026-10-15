"""NAVER API HUB 뉴스 검색 (2026-10-11 확인). 키는 환경 변수 NAVER_CLIENT_ID·NAVER_CLIENT_SECRET (출력 금지).

GET https://naverapihub.apigw.ntruss.com/search/v1/news?query=&display=(≤100)&start=&sort=date
헤더 X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY. 기사 본문은 열지 않고 제목+요약문(description)만 쓴다.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"


class NewsBlocked(RuntimeError):
    """401·403·429 → 멈춘다."""


def search(query: str, display: int = 100, start: int = 1, sleep=time.sleep) -> list[dict]:
    h = {"X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"], "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"]}
    q = urllib.parse.urlencode({"query": query, "display": display, "start": start, "sort": "date"})
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers=h), timeout=30) as r:
                return [item(it) for it in json.load(r).get("items", [])]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise NewsBlocked(f"HTTP {e.code}") from None
            sleep(2 ** i)
        except OSError:
            sleep(2 ** i)
    raise OSError(f"뉴스 검색 실패: {query}")


def item(it: dict) -> dict:
    text = html.unescape(re.sub(r"<[^>]+>", "", f"{it.get('title', '')} {it.get('description', '')}"))
    return {"id": it.get("originallink") or it.get("link"), "text": text, "pub": parsedate_to_datetime(it["pubDate"]).date()}
