import io
import json
from datetime import datetime

from collector import telegram as T
from jobs.notify import eok, tag


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Db:
    def __init__(self): self.sql = []
    def query(self, sql): self.sql.append(sql); return []


def test_tag_and_eok():
    assert eok(143000) == "14.3억" and eok(9500) == "9,500만"
    d = {"price_10k": 150000, "ref_10k": 140000, "prev_high_10k": 148000, "deal_type": "중개", "floor": 10}
    assert tag(d) == " (+7.1%) 🔺신고가"
    d = {"price_10k": 130000, "ref_10k": 140000, "prev_high_10k": 150000, "deal_type": "중개", "floor": 10}
    assert tag(d) == " (-7.1%) 🔻급매"
    assert "급매" not in tag({**d, "floor": 1}) and "급매" not in tag({**d, "deal_type": "직거래"})


def test_send_quiet_chat_and_split(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(T, "select", lambda db, sql: [])
    calls = []

    def opener(req, timeout=0):
        m = req.full_url.rsplit("/", 1)[1]
        calls.append((m, req.data.decode()))
        if m == "getUpdates":
            return _Resp(json.dumps({"ok": True, "result": [{"message": {"chat": {"id": 42}}}]}).encode())
        return _Resp(b'{"ok": true}')
    db = _Db()
    assert T.send(db, "hi", opener, now=datetime(2026, 10, 21, 23, 0, tzinfo=T.KST)) == "quiet"
    assert T.send(db, "a" * 8000, opener, now=datetime(2026, 10, 21, 9, 30, tzinfo=T.KST)) == "sent"
    assert [c[0] for c in calls] == ["getUpdates", "sendMessage", "sendMessage", "sendMessage"]   # 3900자씩 나눔
    assert "chat_id=42" in calls[1][1] and "tg_chat" in db.sql[0]                                 # 대화 번호를 DB 에 저장
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    assert T.send(db, "hi", opener) == "off"


def test_ask_reminder():
    from datetime import date
    from jobs.notify import ask_reminder
    info = {"a": {"name": "가", "ask_last": "2026-10-01"}, "b": {"name": "나", "ask_last": "2026-10-20"}, "c": {"name": "다", "ask_last": None}}
    out = ask_reminder(info, ["a", "b", "c"], date(2026, 10, 26))
    assert "가 10/01" in out[1] and "나" not in out[1] and "저장한 적 없음 1곳: 다" in out[2]
    assert ask_reminder({"b": info["b"]}, ["b"], date(2026, 10, 26)) == []


def test_restore_check_string_values():
    from jobs.user_state_restore import check
    # psql 은 jsonb 문자열 "84" 를 글자 84 로 준다 → 숫자로 바꿔 비교하면 '다름'이 됐던 것(2026-10-26 백업 시험)
    assert check({"v2-area": "84", "w": [1]}, {"v2-area": "84", "w": "[1]"}) == 0
    assert check({"w": [1]}, {"w": "[1]", "x": "1"}) == 1
