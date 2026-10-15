-- F1 과거 입주 반응 (sql/f1_react.sql). 📖 입주 물량이 전세를 누른다 p.154, p.423, 반응표 p.63
CREATE TABLE IF NOT EXISTS presale_react (
  house_no    TEXT PRIMARY KEY,
  lifezone_id TEXT NOT NULL,
  move_in_ym  TEXT NOT NULL,
  total_hh    INTEGER NOT NULL,
  zone_chg    NUMERIC(6, 2),    -- 같은 생활권 기존 단지 전세: 입주 후 6개월 ÷ 입주 전 6개월 − 1 (%)
  base_chg    NUMERIC(6, 2),    -- 같은 시도(그 생활권 제외) 같은 비교 (%)
  rel         NUMERIC(6, 2),    -- zone − base (%p). 음수 = 입주 때 전세가 더 눌림
  n           INTEGER           -- 생활권 쪽 단지·면적군 수
);
ALTER TABLE presale_react ENABLE ROW LEVEL SECURITY;
ALTER TABLE lifezone
  ADD COLUMN IF NOT EXISTS f1_react_rel NUMERIC(6, 2),   -- 그 생활권 과거 큰 입주들의 rel 중앙값 (%p)
  ADD COLUMN IF NOT EXISTS f1_react_n   INTEGER;         -- 사건 수
