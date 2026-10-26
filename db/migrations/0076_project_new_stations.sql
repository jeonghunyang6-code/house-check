-- 철도 사업의 새 역(가칭) [[이름, 위도, 경도], ...] — collector/projects.py new_stations. 위치는 기사 지명 기준 대략, 지도 표시용
ALTER TABLE transit_projects ADD COLUMN IF NOT EXISTS new_stations JSONB;
