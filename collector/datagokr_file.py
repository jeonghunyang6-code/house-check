"""공공데이터포털 파일데이터 내려받기 (화면의 '다운로드' 버튼과 같은 순서, 2026-10-14 확인).

1) 데이터 페이지(/data/<pk>/fileData.do 또는 standard.do)에서 publicDataDetailPk(uddi:…)
2) POST /tcs/dss/selectFileDataDownload.do → atchFileId, fileDetailSn
3) POST /cmm/cmm/check-limit.json → needCaptcha 이면 **멈춘다**(보안문자 우회 금지)
4) GET /cmm/cmm/fileDownload.do?atchFileId=&fileDetailSn=&dataNm=
키가 필요 없는 공개 파일이다. 사이트가 자주 끊겨 단계마다 재시도한다.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

BASE = "https://www.data.go.kr"
UA = {"User-Agent": "house-check (personal research)"}


class DownloadError(RuntimeError):
    pass


class CaptchaRequired(DownloadError):
    """다운로드 횟수 제한으로 보안문자를 요구함 → 멈춘다."""


def _req(url: str, data: dict | None = None, tries: int = 4, sleep=time.sleep) -> bytes:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=UA), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise CaptchaRequired(f"HTTP {e.code}") from None
            last = e
        except Exception as e:  # noqa: BLE001 - 연결 끊김·시간 초과
            last = e
        sleep(5 * (i + 1))
    raise DownloadError(f"{type(last).__name__}: {last}")


def download(pk: str, kind: str = "fileData", sleep=time.sleep) -> tuple[str, bytes]:
    page = _req(f"{BASE}/data/{pk}/{kind}.do", sleep=sleep).decode("utf-8", "replace")
    m = re.search(r"fn_fileDataDown\('(\d+)',\s*'(uddi:[^']+)',\s*'([^']*)',\s*'(\d+)'", page)
    if not m:
        raise DownloadError(f"{pk}: 다운로드 버튼을 찾지 못함")
    _, detail, atch, sn = m.groups()
    info = json.loads(_req(f"{BASE}/tcs/dss/selectFileDataDownload.do",
                           {"publicDataDetailPk": detail, "publicDataPk": pk, "atchFileId": atch, "fileDetailSn": sn,
                            "publicDataTyCode": "PR0051"}, sleep=sleep))
    if not info.get("status"):
        raise DownloadError(f"{pk}: {info.get('error') or '다운로드 정보 없음'}")
    atch, sn = info["atchFileId"], str(info["fileDetailSn"])
    d = info.get("dataSetFileDetailInfo") or {}
    name = d.get("dataNm") or d.get("publicDataSj") or pk
    lim = json.loads(_req(f"{BASE}/cmm/cmm/check-limit.json", {"atchFileId": atch, "fileDetailSn": sn}, sleep=sleep) or b"{}")
    if lim.get("needCaptcha"):
        raise CaptchaRequired(f"{pk}: 다운로드 제한(보안문자) — 멈춤")
    data = _req(f"{BASE}/cmm/cmm/fileDownload.do?" + urllib.parse.urlencode({"atchFileId": atch, "fileDetailSn": sn, "dataNm": name}),
                sleep=sleep)
    return name, data
