-- 일괄 매매일: 같은 단지·같은 날 직거래 🔧5건 이상 (2026-11-02 사용자 요청, docs/BENCHMARK_GAP.md 통계 #3).
-- 기준 '같은 날 5건 이상'은 외부 서비스(집의 기준) 거래량 통계의 일괄매입 제외 기준이고 작가 기준이 아니다(🔧).
-- 직거래에만 적용: DB 의 같은 날 5건+ 608곳 중 상위는 전부 직거래(에드가휘경 313건 등 민간임대·도시형 일괄 매입)였고,
-- 같은 날 중개 여러 건은 잠실엘스·파크리오 2025-03-22(토허 해제 뒤)처럼 규제 발표 앞뒤로 실제 매수가 몰린 날이라 빼지 않는다.
-- 가격 지표(A1 등)는 원래 중개만 쓰므로 영향 없음. 거래량(서울 월 거래량·C1)·직거래 비중(C5)·회전율(C2)에서 뺀다.
CREATE OR REPLACE VIEW deal_bulk_days AS
SELECT apt_seq, contract_date, count(*) AS n
FROM deals
WHERE NOT is_cancelled AND deal_type = '직거래' AND apt_seq IS NOT NULL
GROUP BY 1, 2
HAVING count(*) >= 5;
