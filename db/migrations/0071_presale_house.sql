-- 분양 단지 ↔ 청약홈 분양정보(presale) 연결을 저장(jobs/right_deals.py match_presale). 이름 포함 일치 → 안 되면 같은 시도·주소에 동 이름·이름 유사도 0.6+·번호(숫자·Ⅰ~Ⅹ) 같음
ALTER TABLE presale_complexes ADD COLUMN IF NOT EXISTS house_no TEXT;
ALTER TABLE presale_complexes ADD COLUMN IF NOT EXISTS house_match TEXT;   -- 'name' | 'fuzzy:0.74'
