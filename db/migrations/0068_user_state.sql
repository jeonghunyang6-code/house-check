-- 웹 화면의 개인 기록(관심 단지·임장·호가 붙여넣기·단지 번호 연결·평형)과 텔레그램 대화 번호. 키 하나에 JSON 하나.
-- 웹(web/api/state.js)은 HC_KEY 를 아는 요청만 읽고 쓴다. 알림(jobs/notify.py)은 v2-watch2 로 관심 단지를 안다
CREATE TABLE IF NOT EXISTS user_state (
  k          TEXT PRIMARY KEY,
  v          JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE user_state ENABLE ROW LEVEL SECURITY;
