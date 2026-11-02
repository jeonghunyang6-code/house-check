"""정부 공식 보도자료로 정책 자동 추가 확인 (jobs/policy_news.py, 0082 policy_news.official). 2026-11-02 사용자 요청 ②.

정책브리핑(korea.kr) RSS 의 보도자료 제목에서 같은 종류(collector/policy_news.KINDS)·부동산 말이 있고 날짜가 발표일 ±1일이면 공식 확인.
**2026-11-02 Actions 에서 확인: 정책브리핑 RSS 는 서비스 중단(rssList.do '제공 중단 안내', 피드 주소 404).** 부처 목록 페이지는
국토부 = 307 리디렉트 반복(자동 접속 차단으로 보고 우회하지 않음), 기재부 = 빈 응답, 금융위 = 열림(대출만 해당). 그래서 FEEDS 를 비워
공식 확인을 꺼 둔다('자동' 표시가 남는다). 새 공식 경로를 찾으면 FEEDS 에 넣고 policy_news.yml 수동 실행의 점검 로그로 확인한다.
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

from collector.policy_news import KINDS

FEEDS: tuple[str, ...] = ()   # 정책브리핑 RSS 중단(위). 예전 주소: https://www.korea.kr/rss/dept_molit.xml 등 → 404
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


LISTS = ("https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp", "https://www.fsc.go.kr/no010101", "https://www.moef.go.kr/nw/nes/nesdta.do")


def probe(opener=urllib.request.urlopen) -> None:
    """부처 보도자료 목록 페이지가 열리는지·제목 모양(점검용, RSS 가 2026 중단됨)."""
    for u in LISTS:
        try:
            with opener(urllib.request.Request(u, headers={"User-Agent": "house-check/1.0 (+personal)"}), timeout=20) as r:
                body = r.read().decode("utf-8", "replace")
            print(f"  {u}: {len(body):,}자")
            for m in re.findall(r"<a[^>]+href=\"([^\"]{5,200})\"[^>]*>\s*([^<]{8,120})</a>", body)[:25]:
                print("    …", m[1].strip()[:70], "|", m[0][:100])
            for m in sorted(set(re.findall(r"20\d\d[.-]\d\d[.-]\d\d", body)))[-5:]:
                print("    날짜", m)
        except Exception as e:
            print(f"  {u}: {type(e).__name__} {str(e)[:80]}")


if __name__ == "__main__":   # 피드 점검(policy_news.yml 수동 실행 때): 피드마다 받은 건수와 최근 제목
    probe()
    got, bad = fetch()
    print(f"보도자료 {len(got)}건, 못 받은 피드 {len(bad)}")
    for e in bad:
        print("  ✗", e)
    for x in sorted(got, key=lambda x: x["d"], reverse=True)[:8]:
        print("  ", x["d"], x["src"], x["t"][:60])
