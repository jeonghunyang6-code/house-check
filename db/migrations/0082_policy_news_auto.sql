-- 정책 발표 자동 추가(2026-11-02 사용자 요청 ①②③). policy_news 후보 중 언론사 🔧5곳 이상이 이틀 이상 보도하면 status='auto' 로
-- 화면 정책 목록에 바로 넣는다('자동' 표시). 정책브리핑 보도자료와 맞으면 official 을 채워 '자동' 표시를 뗀다.
-- 텔레그램에 '빼줘' 로 답하면 status='removed'(목록에서 빠짐). 사람이 확인해 collector/policy.py 에 넣으면 'added'.
ALTER TABLE policy_news ADD COLUMN IF NOT EXISTS last_date DATE;      -- 결정 기사가 마지막으로 나온 날(이틀 이상 보도 판정)
ALTER TABLE policy_news ADD COLUMN IF NOT EXISTS title TEXT;          -- 자동 추가 때 화면 제목(첫 기사 제목)
ALTER TABLE policy_news ADD COLUMN IF NOT EXISTS official JSONB;      -- 맞는 정부 보도자료 {t, u, d, src}
ALTER TABLE policy_news ADD COLUMN IF NOT EXISTS auto_at TIMESTAMPTZ;
ALTER TABLE policy_news DROP CONSTRAINT IF EXISTS policy_news_status_check;
ALTER TABLE policy_news ADD CONSTRAINT policy_news_status_check CHECK (status IN ('new', 'added', 'ignored', 'auto', 'removed'));
UPDATE policy_news SET last_date = (SELECT max((a ->> 'd')::date) FROM jsonb_array_elements(articles) a) WHERE last_date IS NULL;
