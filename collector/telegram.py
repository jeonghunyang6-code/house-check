"""텔레그램 알림 보내기. 봇 토큰은 환경 변수 TELEGRAM_BOT_TOKEN(출력 금지).

대화 번호(chat id)는 TELEGRAM_CHAT_ID 가 있으면 그것, 없으면 DB user_state 'tg_chat', 그것도 없으면 봇이 받은 메시지(getUpdates — 2026-10-27 부터 웹훅(web/api/tg.js)을 걸어 두므로 getUpdates 는 409 로 실패, tg_chat 이 이미 있어 쓰이지 않음)에서
가장 최근 보낸 사람으로 정해 DB 에 저장한다 → 사용자는 봇에게 아무 말이나 한 번 보내 두면 된다.
조용한 시간(22~07시 KST)에는 보내지 않는다(알림은 그 시간에 돌지 않게 짰지만 늦게 돈 경우 대비).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from collector.db import Db, lit, select

API = "https://api.telegram.org/bot{token}/{method}"
KST = ZoneInfo("Asia/Seoul")
QUIET = (22, 7)


class TelegramError(RuntimeError):
    pass


def _call(method: str, params: dict, opener=urllib.request.urlopen) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN 없음")
    req = urllib.request.Request(API.format(token=token, method=method), data=urllib.parse.urlencode(params).encode())
    try:
        with opener(req, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:   # 토큰이 들어간 주소는 찍지 않는다
        raise TelegramError(f"HTTP {e.code} {method}") from None
    if not d.get("ok"):
        raise TelegramError(f"{method}: {d.get('description', '')[:100]}")
    return d


def enabled() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def quiet(now: datetime | None = None) -> bool:
    h = (now or datetime.now(KST)).hour
    return h >= QUIET[0] or h < QUIET[1]


def chat_id(db: Db, opener=urllib.request.urlopen) -> str | None:
    if os.environ.get("TELEGRAM_CHAT_ID"):
        return os.environ["TELEGRAM_CHAT_ID"]
    got = select(db, "SELECT v FROM user_state WHERE k = 'tg_chat'")
    if got:
        v = got[0]["v"]
        return str(json.loads(v) if isinstance(v, str) else v)
    ups = _call("getUpdates", {"limit": 20}, opener).get("result", [])
    chats = [u[k]["chat"]["id"] for u in ups for k in ("message", "edited_message", "my_chat_member") if k in u and "chat" in u[k]]
    if not chats:
        return None
    cid = str(chats[-1])
    db.query(f"INSERT INTO user_state (k, v) VALUES ('tg_chat', {lit(json.dumps(cid))}::jsonb) ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now();")
    return cid


def send(db: Db, text: str, opener=urllib.request.urlopen, now: datetime | None = None, force: bool = False) -> str:
    """보냈으면 'sent', 아니면 이유('off'·'quiet'·'no_chat'). force = 사람이 직접 누른 시험은 조용한 시간에도."""
    if not enabled():
        return "off"
    if quiet(now) and not force:
        return "quiet"
    cid = chat_id(db, opener)
    if not cid:
        return "no_chat"
    for i in range(0, len(text), 3900):   # 한 메시지 4096자 제한
        _call("sendMessage", {"chat_id": cid, "text": text[i:i + 3900], "parse_mode": "HTML", "disable_web_page_preview": "true"}, opener)
    return "sent"
