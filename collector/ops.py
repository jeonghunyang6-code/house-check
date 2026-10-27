"""자동 작업(GitHub Actions) 실패 모으기 — jobs/notify.py daily 가 텔레그램 한 줄씩(2026-10-27 사용자 요청).

Actions 안에서만: GITHUB_TOKEN(github.token, actions: read)·GITHUB_REPOSITORY·GITHUB_REF_NAME(기본 브랜치).
기본 브랜치에서 돈 실패만(작업 브랜치 시험 실행 제외). 실패한 단계 이름까지. 지난번 알린 때(user_state 'ops_seen') 뒤 것만.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
# 사용자에게 보이는 이름. IMPORTANT = 화면·알림·기록이 멈추는 작업(⚠️), 나머지는 다음 실행에 다시 하는 보조 작업(▫️)
LABEL = {"daily-snapshot": "실거래 수집", "site": "사이트 배포", "notify": "텔레그램 알림", "backup": "개인 기록 백업", "rights": "분양권·입주권 수집",
         "redev": "정비구역", "policy_news": "정책 발표 감지", "rone": "부동산원 지수", "presale": "청약·입주 예정", "kapt": "K-apt 단지 정보",
         "geo": "단지 좌표", "drive": "출퇴근 차 시간", "bldg": "건축물대장", "infra": "생활 인프라", "searchtrend": "검색량",
         "lifezone": "생활권", "deal-archive": "거래 보관", "auction": "경매", "b5-history": "B5 이력", "maint": "DB 정리", "backfill": "과거 자료 채우기"}
IMPORTANT = {"daily-snapshot", "site", "notify", "backup", "rights"}


class OpsError(RuntimeError):
    pass


def _get(path: str, token: str, opener=urllib.request.urlopen) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                                     "User-Agent": "house-check"})
    try:
        with opener(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001 - 알림 본문은 보내야 하므로 여기서 멈추지 않는다
        raise OpsError(f"{type(e).__name__}: {e}") from None


def failures(since: datetime, opener=urllib.request.urlopen) -> list[dict] | None:
    """since 뒤 기본 브랜치에서 실패한 실행 [{name, label, important, at, step, url}]. Actions 밖이면 None."""
    token, repo, branch = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_REF_NAME")
    if not (token and repo and branch):
        return None
    q = urllib.parse.urlencode({"status": "failure", "branch": branch, "created": ">" + since.strftime("%Y-%m-%dT%H:%M:%SZ"), "per_page": 50})
    out = []
    for run in _get(f"/repos/{repo}/actions/runs?{q}", token, opener).get("workflow_runs", []):
        step = ""
        try:
            for job in _get(f"/repos/{repo}/actions/runs/{run['id']}/jobs", token, opener).get("jobs", []):
                bad = [s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"]
                if bad:
                    step = bad[0]
                    break
        except OpsError:
            pass
        name = run.get("name", "")
        out.append({"name": name, "label": LABEL.get(name, name), "important": name in IMPORTANT, "step": step,
                    "at": datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")), "url": run.get("html_url", "")})
    return sorted(out, key=lambda r: r["at"])


def default_since(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(days=1)
