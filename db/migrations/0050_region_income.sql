-- H6 주민 소득 (관점 D7, 📖 한계 시세 = 그 지역 주민 소득·자산 p.218~219, ▶ D7 0:47). jobs/macro.py --income-only.
-- 국세청 시·군·구별 근로소득 연말정산 신고현황(주소지) KOSIS 133 DT_133001N_4215, 연간 2016~. 사는 곳 기준.
-- 경기는 시 단위라 region_codes 가 여러 개(수원시 → 4개 구에 같은 값). 근로소득만이라 사업·금융소득·자산은 빠진다
CREATE TABLE IF NOT EXISTS region_income (
  year         TEXT    NOT NULL CHECK (year ~ '^[0-9]{4}$'),
  sido         TEXT    NOT NULL,
  name         TEXT    NOT NULL,          -- KOSIS 표기에서 괄호(옛 이름)를 뺀 것
  region_codes TEXT,                      -- 우리 시군구 코드, 쉼표로 (못 맞추면 NULL)
  persons      INTEGER NOT NULL,          -- 연말정산 신고 인원
  pay_mil      BIGINT  NOT NULL,          -- 총급여 합계 (백만원)
  avg_pay_10k  INTEGER NOT NULL,          -- 1인당 총급여 (만원)
  PRIMARY KEY (year, sido, name)
);
ALTER TABLE region_income ENABLE ROW LEVEL SECURITY;
