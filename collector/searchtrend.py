"""R9 인지도 = 검색량 (관점 R9, 📖 인지도는 곧 수요, 남들이 모르는 싼 아파트엔 이유가 있다 p.401, p.409).
네이버 데이터랩 검색어 트렌드(POST https://openapi.naver.com/v1/datalab/search, 하루 1,000회, 한 요청 키워드 묶음 5개).

데이터랩 값은 한 요청 안에서 가장 많이 검색된 묶음·달을 100 으로 둔 상대값이라 요청끼리 비교가 안 된다.
→ 요청마다 기준 단지(ANCHOR, 헬리오시티)를 넣고 '단지 월평균 ÷ 기준 월평균' 을 인지도 지수로 쓴다(헬리오시티 = 1).
검색이 너무 적은 키워드는 데이터랩이 값을 안 주거나 0 이라 지수 0. 🔧 기준선 없음(순위·값만).
흔한 이름('현대', '우성2차')은 다른 단지와 섞이므로 동 이름을 앞에 붙인다('개포우성2차').
2026-10-19: GitHub·세션의 NAVER 키가 개발자센터 키가 아니라 401(인증 실패) — 실제 응답으로 확인하지 못했다.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from collector.kapt import norm_name
from collector.sources.molit import ApiError, QuotaExceeded

URL = "https://openapi.naver.com/v1/datalab/search"
ANCHOR = ("헬리오시티", ["헬리오시티"])
PER_CALL = 4   # + 기준 1 = 5묶음
GENERIC = re.compile(r"^(현대|삼성|대림|한신|우성|삼익|한양|극동|동아|주공|럭키|벽산|신동아|쌍용|롯데|대우|금호|코오롱|두산|풍림|동부|청구|건영|"
                     r"라이프|선경|미성|한진|경남|태영|성원|우방|삼호|진로|엘지|lg|sk|삼환|한라|동신|신안|대명|이수|길훈|세종|대주|"
                     r"보람|한일|국제|중앙|신원|화성|효성|임광|신성|대성|한국|e편한세상|래미안|자이|푸르지오|아이파크|힐스테이트)"
                     r"[0-9]*(차|단지)?$")


def keyword(apt_name: str, umd_name: str | None) -> str | None:
    """검색어. 이름이 너무 짧으면 None, 흔한 이름이면 동 이름(‘동’ 뺀 것)을 앞에 붙인다."""
    n = norm_name(apt_name)
    if len(n) < 2:
        return None
    if GENERIC.match(n) or len(n) < 3:
        stem = re.sub(r"\d*동\d*가?$", "", umd_name or "")
        return stem + n if stem else None
    return n


def body(start: str, end: str, groups: list[tuple[str, list[str]]]) -> dict:
    return {"startDate": start, "endDate": end, "timeUnit": "month",
            "keywordGroups": [{"groupName": g, "keywords": kw} for g, kw in [ANCHOR, *groups]]}


def call(b: dict) -> dict:
    req = urllib.request.Request(URL, data=json.dumps(b).encode(), method="POST", headers={
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"], "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:200]
        if e.code == 429:
            raise QuotaExceeded(msg) from None
        raise ApiError(f"HTTP {e.code} {msg}") from None


def index(resp: dict, months: int) -> dict[str, dict]:
    """응답 → {묶음 이름: {avg, months_with_data, idx}}. idx = 묶음 월평균 ÷ 기준 월평균(값 없는 달은 0)."""
    avg = {}
    for r in resp.get("results", []):
        vals = [float(x["ratio"]) for x in r.get("data", [])]
        avg[r["title"]] = (sum(vals) / months, len(vals))
    base = avg.get(ANCHOR[0], (0.0, 0))[0]
    return {g: {"avg": round(a, 3), "n": n, "idx": round(a / base, 3) if base > 0 else None}
            for g, (a, n) in avg.items() if g != ANCHOR[0]}
