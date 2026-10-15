-- E4 한계 시세, E5 대형/중형 평당가 비율, E7 연식대별 평당가 (sql/metrics.sql 6·7)
-- E4 📖 하급지 84㎡ 천장 = 상급지 59㎡ 가격 p.217~219, p.228 / 단지 안 평형 압축 p.231
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e4_cap_10k  INTEGER;       -- 84㎡ 행만: E3 비교 단지 59㎡(55~64) 기준 시세 중앙값
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e4_cap_n    INTEGER;       -- 59㎡ 기준 시세가 있는 비교 단지 수
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e4_compress NUMERIC(5, 3); -- 단지 단위: 큰 평형 ㎡당 추가 가격 ÷ 59→84 ㎡당 추가 가격 (최근 1년)
ALTER TABLE complex_metrics ADD COLUMN IF NOT EXISTS e4_sizes    TEXT;          -- 압축 계산에 쓴 평형과 가격 '59㎡ 11.0억 / 84㎡ 13.0억 / 114㎡ 14.0억'
-- E5 📖 대형 평형 평당가는 눌린다, 비싼 지역일수록 비슷 p.247~250, p.468 / E7 📖 신축 5천 → 준신축 4천 → 구축 3천 p.56
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e5_ratio   NUMERIC(5, 3);  -- 단지별 (전용 100~135 ㎡당) ÷ (75~100 ㎡당) 의 생활권 중앙값
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e5_n       INTEGER;
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e7_new_ppm NUMERIC(8, 1);  -- 신축(준공 5년 이내) 단지 ㎡당 중앙가(만원)의 중앙값
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e7_mid_ppm NUMERIC(8, 1);  -- 준신축 6~15년
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e7_old_ppm NUMERIC(8, 1);  -- 구축 16년+
ALTER TABLE lifezone ADD COLUMN IF NOT EXISTS e7_n       TEXT;           -- 단지 수 '신축/준신축/구축' 예 '3/5/12'
