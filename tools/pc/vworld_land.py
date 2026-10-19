"""PC(국내 IP)에서 돌리는 VWorld 토지특성 조회 — 단지 대지면적 보충용 (H5 재건축 용적률·대지지분).

VWorld(api.vworld.kr)는 클라우드 서버·GitHub Actions(해외 IP)에서 접속이 끊겨(2026-10-19 확인) 사용자 PC 에서 돌린다.
DB 비밀번호는 필요 없다. 입력: 같은 폴더의 vworld_targets.csv(필지 목록) / 출력: vworld_land_result.csv(필지별 면적).
출력 파일을 Claude 와의 대화에 첨부하면 DB 에 넣는다.

    (Windows 명령 프롬프트)
    set VWORLD_API_KEY=발급받은키
    python vworld_land.py

- 키는 환경 변수 VWORLD_API_KEY 로만 읽는다. 화면·파일에 키를 쓰지 않는다
- 중간에 끊겨도 다시 실행하면 이미 받은 필지는 건너뛴다
- 접속 거부(403)·호출 한도(429)·키 오류가 나오면 멈춘다(우회하지 않음)
- 응답 항목 이름(lndpclAr 등)은 VWorld 문서 기준이고 이 저장소에서 실제 응답으로 확인하지 못했다. 처음 한 건의 응답 모양을 화면에 보여 준다
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = HERE / "vworld_targets.csv"
OUT = HERE / "vworld_land_result.csv"
URL = "https://api.vworld.kr/ned/data/getLandCharacteristics"
COLS = ("pnu", "stdr_year", "land_area", "jimok", "use_zone", "price_per_m2", "status")
PAUSE = 0.15          # 호출 사이 쉬는 시간(초)
FAIL_STREAK = 10


class Stop(Exception):
    pass


def call(key: str, pnu: str, year: int, domain: str) -> dict:
    q = {"key": key, "pnu": pnu, "stdrYear": str(year), "format": "json", "numOfRows": "10", "pageNo": "1"}
    if domain:
        q["domain"] = domain
    try:
        with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(q), timeout=30) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Stop(f"HTTP {e.code} — 접속 거부 또는 호출 한도. 멈춥니다") from None
        raise
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise ValueError("JSON 이 아닌 응답: " + body[:200].replace(key, "***")) from None


def parse(d: dict) -> list[dict]:
    """응답 → 필지 행. 오류 응답이면 Stop/ValueError."""
    if "response" in d and isinstance(d["response"], dict) and d["response"].get("status") == "ERROR":
        err = d["response"].get("error", {})
        msg = f"{err.get('code')} {err.get('text')}"
        if any(k in msg for k in ("KEY", "DOMAIN", "LIMIT", "OVER")):
            raise Stop("VWorld 오류: " + msg)
        raise ValueError("VWorld 오류: " + msg)
    f = (d.get("landCharacteristicss") or {}).get("field") or []
    return f if isinstance(f, list) else [f]


def main() -> int:
    key = os.environ.get("VWORLD_API_KEY", "").strip()
    if not key:
        print("VWORLD_API_KEY 환경 변수가 없습니다. 명령 프롬프트에서 먼저: set VWORLD_API_KEY=발급받은키")
        return 1
    domain = os.environ.get("VWORLD_DOMAIN", "").strip()   # 키를 만들 때 적은 서비스 URL 이 필요하다는 오류가 나면 설정
    pnus = sorted({r["pnu"] for r in csv.DictReader(TARGETS.open(encoding="utf-8"))})
    done = set()
    if OUT.exists():
        done = {r["pnu"] for r in csv.DictReader(OUT.open(encoding="utf-8"))}
    todo = [p for p in pnus if p not in done]
    print(f"필지 {len(pnus):,}개 중 받은 것 {len(done):,}개, 남은 것 {len(todo):,}개")
    new = not OUT.exists()
    years = (date.today().year - 1, date.today().year - 2)
    shown, streak, n = False, 0, 0
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
        try:
            for pnu in todo:
                row = None
                try:
                    for y in years:
                        d = call(key, pnu, y, domain)
                        if not shown:
                            print("첫 응답 모양(확인용):", json.dumps(d, ensure_ascii=False)[:400])
                            shown = True
                        fs = parse(d)
                        if fs:
                            x = fs[0]
                            row = (pnu, x.get("stdrYear") or y, x.get("lndpclAr"), x.get("lndcgrCodeNm"), x.get("prposArea1Nm"),
                                   x.get("pblntfPclnd"), "ok")
                            break
                        time.sleep(PAUSE)
                    streak = 0
                except Stop:
                    raise
                except Exception as e:   # 한 필지 실패는 기록하고 넘어간다
                    streak += 1
                    print(f"  {pnu}: 실패 {str(e)[:120]}")
                    if streak >= FAIL_STREAK:
                        raise Stop(f"{streak}번 연속 실패. 인터넷 연결이나 키를 확인한 뒤 다시 실행하세요") from None
                    time.sleep(3)
                    continue
                w.writerow(row or (pnu, "", "", "", "", "", "none"))
                n += 1
                if n % 200 == 0:
                    f.flush()
                    print(f"  {n:,}/{len(todo):,}")
                time.sleep(PAUSE)
        except Stop as e:
            print(str(e))
            print(f"이번에 {n:,}개 저장. 문제를 해결한 뒤 다시 실행하면 이어서 받습니다.")
            return 2
        except KeyboardInterrupt:
            print(f"\n중단. 이번에 {n:,}개 저장. 다시 실행하면 이어서 받습니다.")
            return 2
    print(f"끝. 이번에 {n:,}개 저장 → {OUT.name} 를 Claude 대화에 첨부해 주세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
