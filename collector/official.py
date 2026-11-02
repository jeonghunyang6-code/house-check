"""정부 공식 보도자료로 정책 자동 추가 확인 (jobs/policy_news.py, 0082 policy_news.official). 2026-11-02 사용자 요청 ②.

정책브리핑(korea.kr) RSS 의 보도자료 제목에서 같은 종류(collector/policy_news.KINDS)·부동산 말이 있고 날짜가 발표일 ±1일이면 공식 확인.
이 클라우드 세션에서는 korea.kr 이 막혀 있어 실제 피드 주소·모양은 GitHub Actions 에서 처음 확인한다(못 받으면 확인을 건너뛰고 '자동' 표시가 남는다).
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

from collector.policy_news import KINDS

FEEDS = (   # 부처별 브리핑(국토부·금융위·기재부·재경부) + 보도자료 전체. 주소가 바뀌면 여기만
    "https://www.korea.kr/rss/dept_molit.xml",
    "https://www.korea.kr/rss/dept_fsc.xml",
    "https://www.korea.kr/rss/dept_moef.xml",
    "https://www.korea.kr/rss/dept_mof.xml",
    "https://www.korea.kr/rss/pressrelease.xml",
)
HOUSING = re.compile(r"주택|부동산|아파트|토지거래|택지|주담대|주택담보|가계대출|양도세|양도소득세|종부세|보유세|취득세|규제지역|조정대상|투기과열")
NEAR = 1   # 발표일 ±1일


def parse(xml: bytes, src: str = "") -> list[dict]:
    """RSS 2.0 → [{t, u, d, src}]. 날짜를 못 읽은 항목은 버린다."""
    out = []
    for it in ET.fromstring(xml).iter("item"):
        t, u, p = (it.findtext("title") or "").strip(), (it.findtext("link") or "").strip(), it.findtext("pubDate") or ""
        try:
            d = parsedate_to_datetime(p).date()
        except (TypeError, ValueError):
            continue
        if t:
            out.append({"t": t, "u": u, "d": d.isoformat(), "src": src})
    return out


def fetch(feeds=FEEDS, opener=urllib.request.urlopen) -> tuple[list[dict], list[str]]:
    """모든 피드의 보도자료와, 못 받은 피드의 이유."""
    items, errs = [], []
    for f in feeds:
        try:
            with opener(urllib.request.Request(f, headers={"User-Agent": "house-check/1.0 (+personal)"}), timeout=20) as r:
                items += parse(r.read(), f.rsplit("/", 1)[-1])
        except Exception as e:   # 피드 하나가 막혀도 나머지로 확인
            errs.append(f"{f.rsplit('/', 1)[-1]}: {type(e).__name__} {str(e)[:80]}")
    return items, errs


def match(kind: str, first: date, items: list[dict]) -> dict | None:
    """같은 종류 말 + 부동산 말이 제목에 있고 발표일 ±NEAR 일인 첫 보도자료."""
    pat = KINDS.get(kind)
    if not pat:
        return None
    lo, hi = first - timedelta(days=NEAR), first + timedelta(days=NEAR)
    for x in items:
        if lo <= date.fromisoformat(x["d"]) <= hi and re.search(pat, x["t"]) and HOUSING.search(x["t"]):
            return x
    return None


INDEX = ("https://www.korea.kr/etc/rssList.do",)


def discover(opener=urllib.request.urlopen) -> list[str]:
    """정책브리핑 안내 페이지에서 RSS 주소(…xml) 후보를 모은다(피드 주소가 바뀌었을 때 점검용)."""
    out = []
    for u in INDEX:
        try:
            with opener(urllib.request.Request(u, headers={"User-Agent": "house-check/1.0 (+personal)"}), timeout=20) as r:
                body = r.read().decode("utf-8", "replace")
            hits = sorted(set(re.findall(r"""(?:https?://www\.korea\.kr)?/[\w/.\-]*rss[\w/.\-]*\.(?:xml|do)[^"'\s<>]*""", body)))
            print(f"  {u}: {len(body):,}자, RSS 후보 {len(hits)}")
            if "rssList" in u:   # 주소 모양을 모를 때: xml·rss 가 들어간 조각을 보여 준다
                for m in sorted(set(re.findall(r".{0,60}(?:\.xml|rss/|Rss|RSS).{0,60}", body)))[:40]:
                    print("    …", m.strip()[:140])
            out += hits
        except Exception as e:
            print(f"  {u}: {type(e).__name__} {str(e)[:80]}")
    return sorted(set(out))


if __name__ == "__main__":   # 피드 점검(policy_news.yml 수동 실행 때): 피드마다 받은 건수와 최근 제목
    for h in discover()[:80]:
        print("   후보", h)
    got, bad = fetch()
    print(f"보도자료 {len(got)}건, 못 받은 피드 {len(bad)}")
    for e in bad:
        print("  ✗", e)
    for x in sorted(got, key=lambda x: x["d"], reverse=True)[:8]:
        print("  ", x["d"], x["src"], x["t"][:60])
