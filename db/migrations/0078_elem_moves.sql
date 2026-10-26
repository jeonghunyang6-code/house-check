-- 초등학교 학생 수·1년 전입·전출(학교알리미 apiType 10, 초등 schulKndCode 02). jobs/infra.py elem. 상세 탭 학교 줄에 숫자만
ALTER TABLE elem_school ADD COLUMN IF NOT EXISTS students INT;
ALTER TABLE elem_school ADD COLUMN IF NOT EXISTS mv_in INT;
ALTER TABLE elem_school ADD COLUMN IF NOT EXISTS mv_out INT;
ALTER TABLE elem_school ADD COLUMN IF NOT EXISTS pban_yr TEXT;
