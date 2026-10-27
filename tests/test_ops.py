import io
import json
from datetime import datetime, timezone

from collector import ops


def test_failures(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    seen = []

    def opener(req, timeout=30):
        seen.append(req.full_url)
        if "/jobs" in req.full_url:
            body = {"jobs": [{"steps": [{"name": "체크아웃", "conclusion": "success"}, {"name": "화면 만들기", "conclusion": "failure"}]}]}
        else:
            body = {"workflow_runs": [{"id": 7, "name": "site", "created_at": "2026-10-27T01:00:00Z", "html_url": "u"},
                                      {"id": 8, "name": "geo", "created_at": "2026-10-26T23:09:55Z", "html_url": "u2"}]}
        return io.BytesIO(json.dumps(body).encode())

    out = ops.failures(datetime(2026, 10, 26, tzinfo=timezone.utc), opener)
    assert [r["label"] for r in out] == ["단지 좌표", "사이트 배포"] and out[1]["important"] and not out[0]["important"]
    assert out[1]["step"] == "화면 만들기" and "branch=main" in seen[0] and "status=failure" in seen[0]


def test_outside_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert ops.failures(datetime(2026, 10, 26, tzinfo=timezone.utc)) is None
