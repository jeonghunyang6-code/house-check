-- H5 경기 정비사업 (collector/redev_gg.py, `python -m jobs.redev --gg-file`). 경기데이터드림 '일반 정비 사업 추진 현황' CSV.
-- openapi.gg.go.kr 는 해외 IP 를 막아(2026-10-20 Actions 확인) 사용자가 PC 에서 받은 파일을 넣는다. 서울(src='seoul')과 같은 표, 출처로 구분
ALTER TABLE redev_zone
  ADD COLUMN IF NOT EXISTS src       TEXT NOT NULL DEFAULT 'seoul',   -- seoul | gg
  ADD COLUMN IF NOT EXISTS vl_old    NUMERIC(6, 1),   -- (기존) 용적률 %
  ADD COLUMN IF NOT EXISTS vl_new    NUMERIC(6, 1),   -- (신축) 계획 용적률 %
  ADD COLUMN IF NOT EXISTS old_built TEXT,            -- 기존 주택 준공연도 ('1980~1992' 처럼 범위도)
  ADD COLUMN IF NOT EXISTS member_hh INTEGER,         -- 조합원 분양 세대
  ADD COLUMN IF NOT EXISTS gen_hh    INTEGER;         -- 일반분양 세대 (경기 원자료 값. 서울은 없어 gen_sale_est 근사)
