-- 1기 신도시 선도지구(collector/newtown.py) 구성 단지 연결: how 에 'newtown' 추가
ALTER TABLE complex_redev DROP CONSTRAINT IF EXISTS complex_redev_how_check;
ALTER TABLE complex_redev ADD CONSTRAINT complex_redev_how_check CHECK (how IN ('jibun', 'name', 'newtown'));
