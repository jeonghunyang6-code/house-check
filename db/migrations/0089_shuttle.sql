-- 회사 셔틀 정류장(2026-11-26 사용자): 통상 근무 출근 승차·퇴근 하차 정류장. 회사 내부 자료라 공개 data.json·저장소에 없다.
-- 넣기: python -m jobs.shuttle_load <노선표.csv> (원본 CSV 는 저장소에 올리지 않는다). 읽기: web/api/shuttle.js(HC_KEY 아는 요청만)
CREATE TABLE IF NOT EXISTS shuttle_stops (
  kind       TEXT NOT NULL CHECK (kind IN ('o', 'h')),   -- o 출근 승차, h 퇴근 하차
  name       TEXT NOT NULL,
  lat        DOUBLE PRECISION NOT NULL,
  lng        DOUBLE PRECISION NOT NULL,
  route      TEXT NOT NULL,
  t_board    TEXT,          -- 출근: 탑승 시각(HH:MM)
  t_arrive   TEXT,          -- 출근: 회사 도착 시각
  hours      TEXT,          -- 퇴근: 회사 출발 시(쉼표, 예 '18,19,20'). 원본 하차 시각은 순서용이라 안 씀
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, name, lat, lng, route)
);
-- 공개 REST(anon·authenticated) 차단: RLS 켜고 정책 없음 + 권한 회수(0003 과 같은 원칙에 한 겹 더)
ALTER TABLE shuttle_stops ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON shuttle_stops FROM anon, authenticated;
