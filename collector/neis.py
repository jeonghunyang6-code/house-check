"""나이스 교육정보 개방 포털 학원·교습소 정보 (acaInsTiInfo, 2026-10-15 확인).

키(NEIS_API_KEY) 없이는 한 번에 5건만 와서 키가 필요하다. 한 번에 최대 1,000건.
좌표가 없어 도로명 주소의 법정동(괄호 안 '(개포동, 삼성빌딩)')이나 읍·면으로 동별 수를 센다.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

URL = "https://open.neis.go.kr/hub/acaInsTiInfo"
UA = {"User-Agent": "house-check (personal research)"}
OFFICES = {"B10": "서울", "E10": "인천", "J10": "경기"}   # 시도교육청 코드
SIDO = {"서울특별시": "서울", "인천광역시": "인천", "경기도": "경기"}
EXAM = "입시.검정 및 보습"                                   # 교습 영역 중 '학원가'로 보는 것
PAGE = 1000


class NeisError(RuntimeError):
    pass


def fetch_page(office: str, page: int, key: str | None = None, sleep=time.sleep) -> tuple[int, list[dict]]:
    key = key or os.environ.get("NEIS_API_KEY", "")
    if not key:
        raise NeisError("NEIS_API_KEY 가 없다")
    q = urllib.parse.urlencode({"KEY": key, "Type": "json", "pIndex": page, "pSize": PAGE, "ATPT_OFCDC_SC_CODE": office})
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers=UA), timeout=60) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise NeisError(f"HTTP {e.code} → 멈춤") from None
            last = e
        except Exception as e:  # noqa: BLE001 - 연결 끊김·시간 초과
            last = e
        sleep(5 * (i + 1))
    else:
        raise NeisError(f"{type(last).__name__}: {last}")
    if "RESULT" in d:                                       # 오류나 데이터 없음은 맨 위에 RESULT 만
        code = d["RESULT"].get("CODE", "")
        if code == "INFO-200":
            return 0, []
        raise NeisError(f"{code} {d['RESULT'].get('MESSAGE', '')}")
    head, body = d["acaInsTiInfo"]
    return int(head["head"][0]["list_total_count"]), body["row"]


def parse_place(road: str | None, detail: str | None) -> tuple[str, str, str] | None:
    """('서울', '강남구', '개포동'). road='서울특별시 강남구 개포로82길 7', detail=', 3층 301호 (개포동, 삼성빌딩)'."""
    t = (road or "").split()
    if len(t) < 3 or t[0] not in SIDO:
        return None
    sido, sgg = SIDO[t[0]], t[1]
    rest = t[2:]
    if sgg.endswith("시") and rest and rest[0].endswith("구"):
        sgg, rest = f"{sgg} {rest[0]}", rest[1:]
    if rest and re.fullmatch(r".+[읍면]", rest[0]):
        return sido, sgg, rest[0]
    m = re.search(r"\(([^,)]+)", detail or "")
    if m and re.fullmatch(r"\S+(동|가)", m.group(1).strip()):
        return sido, sgg, m.group(1).strip()
    return None


def count_by_dong(rows: list[dict]) -> tuple[dict[tuple, dict], int]:
    """개원 상태만. (시도, 시군구, 동) → {n, exam, exam_hagwon}. 동을 못 읽은 수도 돌려준다."""
    out: dict[tuple, dict] = {}
    miss = 0
    for r in rows:
        if (r.get("REG_STTUS_NM") or "").strip() != "개원":
            continue
        p = parse_place(r.get("FA_RDNMA"), r.get("FA_RDNDA"))
        if not p:
            miss += 1
            continue
        c = out.setdefault(p, {"n": 0, "exam": 0, "exam_hagwon": 0})
        c["n"] += 1
        if (r.get("REALM_SC_NM") or "").strip() == EXAM:
            c["exam"] += 1
            if (r.get("ACA_INSTI_SC_NM") or "").strip() == "학원":
                c["exam_hagwon"] += 1
    return out, miss


def match_dong(counts: dict[tuple, dict], sido: str, sgg: str, umd: str) -> tuple | None:
    """단지(시도·시군구·법정동) → counts 의 열쇠. 행정구역 개편(인천 2026-07, 화성 일반구)으로 주소의 시군구 이름이
    다를 수 있어 ① 똑같이 ② 시 이름만 같고 ③ 주소에 그 시군구 이름이 아예 없을 때(개편으로 이름이 바뀐 구)
    시도 안에서 그 동 이름이 하나뿐이면 맞춘다."""
    dong = (umd or "").split()[0] if umd else ""
    if not dong:
        return None
    if (sido, sgg, dong) in counts:
        return sido, sgg, dong
    city = sgg.split()[0]
    same = [k for k in counts if k[0] == sido and k[2] == dong and k[1].split()[0] == city]
    if len(same) == 1:
        return same[0]
    if any(k[0] == sido and k[1] == sgg for k in counts):
        return None
    same = [k for k in counts if k[0] == sido and k[2] == dong]
    return same[0] if len(same) == 1 else None
