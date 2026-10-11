-- Supabase는 public 스키마 표를 REST API(anon 키)로 노출한다. 개인용이라 외부 접근이 필요 없으므로
-- RLS를 켜고 정책은 두지 않는다 → anon/authenticated는 접근 불가, postgres·service_role(수집기)은 RLS를 우회한다.
ALTER TABLE court_jurisdiction ENABLE ROW LEVEL SECURITY;
ALTER TABLE auction_stats      ENABLE ROW LEVEL SECURITY;
