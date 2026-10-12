# 지도 경계 출처

`sudogwon_sgg_20260701.json`은 아래 행정동 경계를 시군구 단위로 합치고 단순화한 것이다(`tools/prototype/geo.py`).
수도권 82개 시군구(옹진군 제외)의 SVG 경로·중심점·면적. 좌표는 경도·위도를 화면 좌표로 바꾼 값이다.

> 본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서
> 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor,
> https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다.

원본 파일: `vuski/admdongkor` 저장소 `ver20260701/HangJeongDong_ver20260701.geojson` (2026-07-01 행정구역).
시군구 코드 83개가 `collector/regions.py`와 일치함을 2026-10-12에 확인했다.
