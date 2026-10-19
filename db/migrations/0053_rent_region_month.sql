-- 전월세 요약 저장 구조 (2026-10-19, 무료 플랜 500MB 유지, jobs/rent_archive.py):
--   rent_monthly(단지 × 면적군 × 달)는 최근 17개월만 DB 에 둔다(D4 전세 1년 변화가 16개월 전까지 본다).
--   그 전 달은 시군구별 보관 파일 rentsum_<시군구>.csv.gz (GitHub Releases raw-data) — F1 입주 반응·시안 전세 차트가 읽는다.
--   지역 합계(신규·갱신 전세 건수, D5)는 전체 기간을 여기 둔다(시군구 × 달이라 작다).
CREATE TABLE IF NOT EXISTS rent_region_month (
  region_code    TEXT    NOT NULL,
  contract_month TEXT    NOT NULL CHECK (contract_month ~ '^[0-9]{6}$'),
  n_jeonse       INTEGER NOT NULL,
  n_jeonse_new   INTEGER NOT NULL,
  n_jeonse_renew INTEGER NOT NULL,
  n_wolse        INTEGER NOT NULL,
  PRIMARY KEY (region_code, contract_month)
);
ALTER TABLE rent_region_month ENABLE ROW LEVEL SECURITY;
INSERT INTO rent_region_month (region_code, contract_month, n_jeonse, n_jeonse_new, n_jeonse_renew, n_wolse)
SELECT region_code, contract_month, sum(n_jeonse), sum(n_jeonse_new), sum(n_jeonse_renew), sum(n_wolse)
FROM rent_monthly GROUP BY 1, 2
ON CONFLICT (region_code, contract_month) DO NOTHING;
