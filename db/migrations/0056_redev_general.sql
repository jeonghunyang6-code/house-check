-- H5 재건축 일반분양 규모 (📖 재건축 사업성: 일반분양이 많을수록 p.374~397). jobs/redev.py 가 연결 단계에서 채운다.
-- 일반분양 근사 = 계획 분양 세대 − 기존 세대(조합원 몫을 기존 세대 수로 근사, 상가 조합원 등은 반영 못 함)
ALTER TABLE redev_zone
  ADD COLUMN IF NOT EXISTS gen_sale_est INTEGER,        -- 일반분양 근사 세대
  ADD COLUMN IF NOT EXISTS gen_ratio    NUMERIC(6, 2),  -- 일반분양 ÷ 기존 세대
  ADD COLUMN IF NOT EXISTS gen_pct      NUMERIC(5, 1);  -- 서울 재건축 구역 중 gen_ratio 가 이 값 이하인 비율 (%)
