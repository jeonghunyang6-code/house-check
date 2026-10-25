-- 재건축 뒤 새 단지: 등기가 끝나 국토부 자료에 새 단지 번호(apt_seq)가 생기면 옛 단지(같은 K-apt 코드·같은 시군구, 준공 10년+ 차이)를 잇는다.
-- 예: 11740-180 코오롱상가아파트(1988) → 11740-7014 더샵강동센트럴시티(2025). 분양권·입주권 거래는 새 단지로 옮기고(jobs/right_deals.py), 화면은 관심 ♡ 등을 옮긴다(v2_pmap)
CREATE OR REPLACE VIEW complex_successor AS
SELECT DISTINCT ON (o.apt_seq) o.apt_seq AS old_seq, n.apt_seq AS new_seq, n.apt_name AS new_name
FROM complexes o JOIN complexes n
  ON n.kapt_code = o.kapt_code AND n.region_code = o.region_code AND n.apt_seq <> o.apt_seq AND n.build_year >= o.build_year + 10
WHERE o.kapt_code IS NOT NULL
ORDER BY o.apt_seq, n.build_year DESC, n.apt_seq;
