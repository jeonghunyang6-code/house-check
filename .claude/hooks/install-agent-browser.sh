#!/usr/bin/env bash
# 클라우드 세션(CLAUDE_CODE_REMOTE=true)에서만 실행한다.
# 로컬 컴퓨터에는 이미 전역 설치되어 있으므로 아무것도 하지 않는다.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

# 1) agent-browser CLI와 브라우저
if ! command -v agent-browser >/dev/null 2>&1; then
  {
    npm install -g agent-browser &&
    (agent-browser install --with-deps || agent-browser install)
  } >/tmp/agent-browser-install.log 2>&1 \
    || echo "agent-browser 설치 실패: /tmp/agent-browser-install.log 참고" >&2
fi

# 2) REA(.mcp.json의 rea 서버)가 쓰는 rea-agents를 미리 받아 둔다.
#    REA는 Node 22.23.4+ / 24.22.1+ / 26.12.1+ 가 필요하다.
npx -y rea-agents@6.10.1 --version >/tmp/rea-install.log 2>&1 \
  || echo "rea-agents 준비 실패(Node 버전 확인 필요): /tmp/rea-install.log 참고" >&2

exit 0
