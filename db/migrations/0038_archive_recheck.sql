-- 전월세 해제 재확인(jobs/rent_archive.recheck)이 보관 파일을 다시 쓴 기록
ALTER TABLE archive_cells DROP CONSTRAINT IF EXISTS archive_cells_source_check;
ALTER TABLE archive_cells ADD CONSTRAINT archive_cells_source_check
  CHECK (source IN ('api_backfill', 'db_rollover', 'recheck'));
