-- 전월세 옛 달 DB → 보관 파일 이관(jobs/rent_archive.py daily)이 2026-11-01 부터 시간 초과로 실패.
-- rents 를 지울 때 외래 키 확인이 지운 행마다 rent_events 를 rent_key 로 찾는데 그 열에 색인이 없어 통째로 훑었다(4.5만 행 × 3.6만 행)
CREATE INDEX IF NOT EXISTS rent_events_rent_key_idx ON rent_events (rent_key);
