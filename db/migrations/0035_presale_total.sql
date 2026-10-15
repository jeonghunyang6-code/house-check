-- F1 총 세대 보정 (jobs/presale.py, collector/presale.py). 청약홈 공급 세대에는 재건축·재개발 조합원 몫이 빠져 있다
ALTER TABLE presale
  ADD COLUMN IF NOT EXISTS imprmn      BOOLEAN,   -- 정비사업 여부 (IMPRMN_BSNS_AT)
  ADD COLUMN IF NOT EXISTS total_hh    INTEGER,   -- 총 세대: K-apt 세대수, 아니면 정비사업 추정, 아니면 공급 세대
  ADD COLUMN IF NOT EXISTS total_basis TEXT,      -- 'K-apt' / '추정 ×r' / '공급'
  ADD COLUMN IF NOT EXISTS kapt_apt_seq TEXT;     -- 맞춘 단지 (complexes.apt_seq)
