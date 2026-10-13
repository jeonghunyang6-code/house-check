-- 급지 E1 (collector/grade.py, jobs/grade.py). 분기마다 새 asof 로 쌓는다. 정의: docs/HANDOFF.md 급지 E1 확정
CREATE TABLE IF NOT EXISTS dong_grade (
  region_code  TEXT     NOT NULL,
  umd_name     TEXT     NOT NULL,
  asof         DATE     NOT NULL,
  grade        SMALLINT NOT NULL CHECK (grade BETWEEN 1 AND 8),  -- 경계 30/25/20/15/12/9/6억
  value_10k    INTEGER  NOT NULL,   -- 84㎡ 환산 실거래 대표가 (300세대 미만 거래 0.3 가중 중앙값)
  q1_10k       INTEGER,             -- 가중 하위 25%
  q3_10k       INTEGER,             -- 가중 상위 25%
  n_complex    INTEGER  NOT NULL,
  n_deals      INTEGER  NOT NULL,
  old_share    NUMERIC(4, 3),       -- 30년+ 단지 거래 비중
  flag_rebuild BOOLEAN  NOT NULL,   -- 재건축 기대: old_share ≥ 0.5
  flag_gap     BOOLEAN  NOT NULL,   -- 동 안 격차 큼: q3 ÷ q1 ≥ 2
  new_big_name TEXT,                -- 신축 대단지 (준공 5년 이내, 1,000세대+) 중 가장 큰 곳
  new_big_10k  INTEGER,             -- 그 단지의 84㎡ 환산가
  PRIMARY KEY (region_code, umd_name, asof)
);
