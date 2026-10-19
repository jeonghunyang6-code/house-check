"""R9 인지도 = 검색량 (관점 R9, 📖 인지도는 곧 수요, 남들이 모르는 싼 아파트엔 이유가 있다 p.401, p.409).
네이버 데이터랩 검색어 트렌드. 2026년부터 신규 이용은 개발자센터가 아니라 NAVER API HUB(네이버 클라우드):
POST https://naverapihub.apigw.ntruss.com/search-trend/v1/search, 헤더 X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY
(시크릿 이름은 NAVER_CLIENT_ID·NAVER_CLIENT_SECRET 그대로, 값은 API HUB 키). 월 50,000회, 한 요청 키워드 묶음 5개.
2026-10-19 이 키로 호출 → 401 "요청한 API는 이 Application에서 활성화되어 있지 않습니다" (키는 유효, 앱에 검색어 트렌드를 켜야 함).

데이터랩 값은 한 요청 안에서 가장 많이 검색된 묶음·달을 100 으로 둔 상대값이라 요청끼리 비교가 안 된다.
→ 요청마다 기준 단지(ANCHOR, 헬리오시티)를 넣고 '단지 월평균 ÷ 기준 월평균' 을 인지도 지수로 쓴다(헬리오시티 = 1).
검색이 너무 적은 키워드는 데이터랩이 값을 안 주거나 0 이라 지수 0. 🔧 기준선 없음(순위·값만).
검색어 묶음(한 묶음 = 키워드 검색량의 합): 이름·이름+'아파트'·동+이름. 2026-10-19 실제 응답: 은마를 '대치은마'로만 찾으면 헬리오시티의 0.02배,
'은마아파트'는 1.56배 — 사람들이 부르는 이름을 다 넣어야 한다. 흔한 이름('현대', '우성2차')은 다른 단지와 섞이므로 동 이름을 붙인 것만('개포우성2차').
응답 모양(results[].title·data[].period·ratio)은 옛 개발자센터와 같다고 보고 짰다 — 실제 응답으로 아직 확인 못 함.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from collector.kapt import norm_name
from collector.sources.molit import ApiError, QuotaExceeded

URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
ANCHOR = ("헬리오시티", ["헬리오시티", "헬리오시티아파트", "가락헬리오시티"])   # 단지 묶음과 같은 규칙
PER_CALL = 4   # + 기준 1 = 5묶음
GENERIC = re.compile(r"^(현대|삼성|대림|한신|우성|삼익|한양|극동|동아|주공|럭키|벽산|신동아|쌍용|롯데|대우|금호|코오롱|두산|풍림|동부|청구|건영|"
                     r"라이프|선경|미성|한진|경남|태영|성원|우방|삼호|진로|엘지|lg|sk|삼환|한라|동신|신안|대명|이수|길훈|세종|대주|"
                     r"보람|한일|국제|중앙|신원|화성|효성|임광|신성|대성|한국|e편한세상|래미안|자이|푸르지오|아이파크|힐스테이트)"
                     r"[0-9]*(차|단지)?$")


def keywords(apt_name: str, umd_name: str | None, other_names: tuple[str, ...] = ()) -> list[str] | None:
    """검색어 묶음(🔧 최대 6개). 이름이 한 글자 이하면 None. 흔한 이름은 동 이름을 붙인 것만(동 이름이 없으면 None).
    other_names: K-apt 단지 이름 등 다른 공식 이름(같은 규칙). 사람들이 부르는 이름('목동7단지')과 공식 이름('목동신시가지7')이
    다르면 여전히 못 잡는다(2026-10-19 확인) → 지수가 거의 0 이면 '인지도 낮음'이 아니라 '검색어로 안 잡힘'으로 본다"""
    stem = re.sub(r"\d*동\d*가?$", "", umd_name or "")
    out: list[str] = []
    for name in (apt_name, *other_names):
        n = norm_name(name)
        if len(n) < 2:
            continue
        if GENERIC.match(n):
            out += [stem + n, stem + n + "아파트"] if stem else []
        else:
            out += [n, n + "아파트"] + ([stem + n] if stem and not n.startswith(stem) else [])
    out = list(dict.fromkeys(out))[:6]
    return out or None


def body(start: str, end: str, groups: list[tuple[str, list[str]]]) -> dict:
    return {"startDate": start, "endDate": end, "timeUnit": "month",
            "keywordGroups": [{"groupName": g, "keywords": kw} for g, kw in [ANCHOR, *groups]]}


def call(b: dict, retries: int = 4) -> dict:
    req = urllib.request.Request(URL, data=json.dumps(b).encode(), method="POST", headers={
        "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"], "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
        "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:200]
            if e.code == 429:
                raise QuotaExceeded(msg) from None
            raise ApiError(f"HTTP {e.code} {msg}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:   # 2026-10-19 3,084곳째에 연결 끊김으로 작업 전체가 죽었다
            if attempt == retries - 1:
                raise ApiError(f"연결 실패 {e}") from None
            time.sleep(2 * 2 ** attempt)
    raise ApiError("unreachable")


def index(resp: dict, months: int) -> dict[str, dict]:
    """응답 → {묶음 이름: {avg, months_with_data, idx}}. idx = 묶음 월평균 ÷ 기준 월평균(값 없는 달은 0)."""
    avg = {}
    for r in resp.get("results", []):
        vals = [float(x["ratio"]) for x in r.get("data", [])]
        avg[r["title"]] = (sum(vals) / months, len(vals))
    base = avg.get(ANCHOR[0], (0.0, 0))[0]
    return {g: {"avg": round(a, 3), "n": n, "idx": round(a / base, 3) if base > 0 else None}
            for g, (a, n) in avg.items() if g != ANCHOR[0]}
