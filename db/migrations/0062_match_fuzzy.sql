-- K-apt 연결 마지막 단계 '이름 유사도'(collector/kapt.py match_complexes, 2026-10-20)
ALTER TABLE complexes DROP CONSTRAINT IF EXISTS complexes_match_method_check;
ALTER TABLE complexes ADD CONSTRAINT complexes_match_method_check CHECK (match_method IN ('jibun', 'road', 'name', 'fuzzy', 'manual'));
