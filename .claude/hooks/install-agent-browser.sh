#!/usr/bin/env bash
# 클라우드 세션에서만 agent-browser CLI와 브라우저를 설치한다.
# 로컬 컴퓨터에는 이미 전역 설치되어 있으므로 아무것도 하지 않는다.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
command -v agent-browser >/dev/null 2>&1 && exit 0
{
  npm install -g agent-browser &&
  (agent-browser install --with-deps || agent-browser install)
} >/tmp/agent-browser-install.log 2>&1 || echo "agent-browser 설치 실패: /tmp/agent-browser-install.log 참고" >&2
exit 0
