-- 0003과 같은 이유로 실거래 표에도 RLS를 켠다 (정책 없음).
ALTER TABLE deals       ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_events ENABLE ROW LEVEL SECURITY;
