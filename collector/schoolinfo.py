"""학교알리미 OpenAPI (www.schoolinfo.go.kr/openApi.do, 키 SCHOOLINFO_API_KEY, 2026-10-15 실제 응답으로 확인).

apiType 0 학교기본정보(SCHUL_CODE, SCHUL_NM, LTTUD 위도, LGTUD 경도), 10 전·출입 및 학업중단 학생 수
(STDNT_SUM 학생 수, MVIN_SUM 전입, MVT_SUM 전출). 학업성취도·졸업생 진로는 OpenAPI 에 없다.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

from collector.infra import dist_m

URL = "https://www.schoolinfo.go.kr/openApi.do"
UA = {"User-Agent": "house-check (personal research)"}
SIDO = {"11": "서울", "28": "인천", "41": "경기"}
MATCH_M = 300          # 학구도 학교와 학교알리미 학교를 같은 학교로 볼 거리


class SchoolInfoError(RuntimeError):
    pass


def fetch(api_type: int, sido: str, year: str, kind: str = "03", key: str | None = None, sleep=time.sleep) -> list[dict]:
    key = key or os.environ.get("SCHOOLINFO_API_KEY", "")
    if not key:
        raise SchoolInfoError("SCHOOLINFO_API_KEY 가 없다")
    q = urllib.parse.urlencode({"apiKey": key, "apiType": api_type, "sidoCode": sido, "schulKndCode": kind, "pbanYr": year})
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers=UA), timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise SchoolInfoError(f"HTTP {e.code} → 멈춤") from None
            last = e
        except Exception as e:  # noqa: BLE001 - 연결 끊김·시간 초과
            last = e
        sleep(5 * (i + 1))
    else:
        raise SchoolInfoError(f"{type(last).__name__}: {last}")
    if d.get("resultCode") != "success":
        raise SchoolInfoError(str(d.get("resultMsg")))
    return d.get("list") or []


def norm_name(s: str) -> str:
    """'서울대치중학교' → '대치중', '단국대학교사범대학부속중학교' → '단국대학교사범대학부속중'."""
    s = re.sub(r"\s+", "", s or "")
    s = re.sub(r"^(서울|인천|경기)", "", s)
    return re.sub(r"중학교$", "중", s)


def net_in_rate(row: dict) -> float | None:
    """(전입 − 전출) ÷ 학생 수 × 100. 학생 수가 없으면 None."""
    try:
        n, i, o = int(row["STDNT_SUM"]), int(row["MVIN_SUM"]), int(row["MVT_SUM"])
    except (KeyError, TypeError, ValueError):
        return None
    return round((i - o) / n * 100, 1) if n > 0 else None


def match(gudo: dict[str, dict], info: list[dict]) -> dict[str, dict]:
    """학구도 학교ID → 학교알리미 행. 이름(정규화)이 같고 MATCH_M 안이면 같은 학교. 이름이 달라도 100m 안 하나뿐이면 같은 학교."""
    pts = []
    for r in info:
        try:
            pts.append((r, float(r["LTTUD"]), float(r["LGTUD"])))
        except (KeyError, TypeError, ValueError):
            continue
    out = {}
    for sid, s in gudo.items():
        near = [(dist_m(s["lat"], s["lng"], la, lo), r) for r, la, lo in pts
                if abs(la - s["lat"]) < 0.01 and abs(lo - s["lng"]) < 0.012]
        named = [x for x in near if x[0] <= MATCH_M and norm_name(x[1].get("SCHUL_NM")) == norm_name(s["name"])]
        if named:
            out[sid] = min(named, key=lambda x: x[0])[1]
            continue
        close = [x for x in near if x[0] <= 100]
        if len(close) == 1:
            out[sid] = close[0][1]
    return out
