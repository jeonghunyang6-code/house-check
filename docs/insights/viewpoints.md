# 송희구 관점 카드 (최종)

두 개의 A등급 출처를 엮었다.

| 출처 | 범위 | 표기 |
|---|---|---|
| 유튜브 `작가 송희구` (@thewriter-song) | 영상·라이브 672개 중 자막 626개 (2022-02 ~ 2026-10), 키워드 상위 영상 위주로 정독. 2026-11-28 추가: 10/11 이후 새 영상 31개 중 자막 있는 15개 정독(10/13~11/27, 사용자 PC 수집 — 클라우드는 유튜브 로봇 확인으로 막힘). 15개는 자막 없음(짧은 영상), 10/11 1개 미수집 | `▶ 제목 m:ss` (해당 시점 링크) |
| 『나의 첫 번째 부동산 교과서』 (서삼독, 2026-06) | 전권 (p.4~477) | `📖 p.쪽` |
| 부읽남TV 출연 "경기 외곽까지 번질 겁니다" [송희구 작가 풀버전] (2026-11-06 촬영, B등급) | 자막 전체(사용자 제공 2026-11-15) | `▶ … m:ss (부읽남TV 출연, B등급, 26-11-06 촬영)` · 시황 발언은 맨 아래 **시점 발언**에 따로 |

- 책은 저작권 보호 대상이므로 저장소에는 **요약과 쪽수만** 남긴다. 원문은 로컬 `data/raw/book/`(git 제외)에만 둔다.
- 자동 자막 오인식이 있을 수 있어, 규칙으로 옮길 때 영상 해당 시점을 확인한다.
- 마지막 열의 지표 ID는 [indicators.md](indicators.md)의 구현 명세를 가리킨다.

---

## 0. 분석기의 원칙 (메타 관점)

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| M1 | **예측하지 않는다.** 투자는 예측이 아니라 선택과 대응. 단일 변수로 시장을 단정하지 않는다 | [▶ 집값의 방향은 어디로 1:32](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=92) | 📖 p.58~61, p.78, p.82 | 점수·예측 대신 **관찰 체크리스트** |
| M2 | 고점·저점은 못 맞추지만 **과열 정도는 관찰로 판단할 수 있다** | [▶ 지금 팔고 하락장 기다릴까 3:49](https://www.youtube.com/watch?v=HWJULtSpT7w&t=229) | 📖 p.111~115 | B5 과열 확산도 |
| M3 | **실거래가 = 시장이 매긴 최종 점수.** 역 위치·거리·인프라·학군이 모두 반영돼 있다. 자체 입지 점수표를 만들지 마라 | [▶ 요즘 호가 진짜 너무 합니다 1:04](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=64) | 📖 p.133~134, p.215~216, **p.356** | 입지 점수 없음. 입지 요소는 "왜 이 가격인가" 설명용 (H군) |
| M4 | **실거래가·거래량·환금성을 교차 검증**하라. 통계는 방향성만 참고 | – | 📖 **p.167**, p.132~133 | 모든 가격 지표에 거래 건수·신뢰도 동반 표시 |
| M5 | 지역 평균 통계는 내 단지와 다르다 (전세가율 지역 65% vs 단지 61%) | [▶ 집값의 방향은 어디로 0:00](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=0) | 📖 p.131~132 | 지역값과 단지값을 항상 나란히 |
| M6 | 숫자보다 **현장 분위기**가 먼저 바뀐다 | [▶ 드디어...시작인가 7:39](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=459) | 📖 p.171~182 임장 체크리스트 | 데이터로 못 잡는 항목은 "현장 확인" 칸 |
| M7 | 정책은 일시적 파도, **소득과 통화량**이 배의 엔진 | [▶ 금리상승의 후폭풍 0:00](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=0) | 📖 p.50, p.291~292 | G1 유동성·소득 지수 |
| M8 | 정보 과잉은 결정을 막는다 | – | 📖 p.471 | 홈 화면은 핵심 신호 소수로 제한 |

## 1. 실거래가·호가·시세

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| P1 | 호가가 아니라 **최근 1~2개월 실거래가**가 기준. 1층 제외, 중층 이상으로 | [▶ 요즘 호가 진짜 너무 합니다 1:33](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=93), [▶ 반등의 속도가 너무 빠르다 1:42](https://www.youtube.com/watch?v=3T1QEM3mQ2A&t=102) | 📖 p.120, p.133~136 | A1 기준 시세 |
| P2 | 최근 실거래 대비 호가 **3%까지 설명 가능, 5% 넘으면 설명 필요** | [▶ 요즘 호가 진짜 너무 합니다 1:56](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=116), [2:36](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=156). 호가만 높아졌다고 오르는 중이거나 상급지라고 판단하지 마라 — 주변이 올랐다·높게 팔렸다는 소문으로 호가를 올린다 [▶ 호가가 비쌀 때 0:22](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=22), [0:43](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=43) | 📖 p.335 배짱 매물 | 호가 소스 확보 시 |
| P3 | 거래 없는 평형은 **같은 단지 인접 평형으로 보간**, 그다음 비슷한 급지 5개 단지 비교 | [▶ 도대체 얼마야? 0:54](https://www.youtube.com/watch?v=QEg2JGLCADo&t=54). 요즘은 같이 움직이는 단지 5개 정도는 봐야(매물이 적다) — 동·층·내부·전망·호가 종합 비교 [▶ 나중에 시세차익 큰 곳 1:21](https://www.youtube.com/watch?v=9f7SKimLzQA&t=81), [1:42](https://www.youtube.com/watch?v=9f7SKimLzQA&t=102). 비슷한 급지·상품성 5개 단지 매물을 다 받아 보고 가장 합리적인 호가를 고른다(10개 보면 5개는 거둬들였거나 올렸거나 이미 팔림) [▶ 호가가 비쌀 때 5:31](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=331), [5:52](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=352) | 📖 p.472~473 (대체 평형 존재 여부) | A5 보간 |
| P4 | **급매 = 실거래 대비 5% 이상 저렴.** 호가 대비 급매는 가짜. 급매가 소진되고 하단이 오르면 반등 | [▶ 부동산 자산가들은 지금 3:28](https://www.youtube.com/watch?v=GUL2aBsyvBE&t=208) | 📖 **p.245~247** | A4 급매 체결 비중 |
| P5 | 실거래는 **거래량과 함께**. 거래가 극히 적으면 급매 한 건이 시세처럼 보인다. 급매·가족 간 거래 제외 | [▶ 왜 점점 차이나는 걸까? 1:05](https://www.youtube.com/watch?v=l3ONoblEkFo&t=65) | 📖 **p.121, p.135~137**, p.401~404 | A2 신뢰도, 전처리 |
| P6 | **층·동 차이**: 저층(1~4층)은 중고층 대비 약 10%, 로얄동 vs 기피동 5~10%, 단지 내 차이 한계 10~15%. 역 1분당 평지 0.5%·언덕 1% | 저층은 중고층 대비 10% 싸야, 탑층은 누수만 없으면 괜찮다(층간소음 없음) [▶ 나중에 시세차익 큰 곳 1:00](https://www.youtube.com/watch?v=9f7SKimLzQA&t=60), [1:21](https://www.youtube.com/watch?v=9f7SKimLzQA&t=81) | 📖 **p.192~195**, p.337, p.464 | 전처리 층 보정, H1 |
| P7 | 실물자산은 최소 **물가만큼은** 오른다 (인구·경제기반 약화 지역은 예외) | 장기 우상향의 가장 큰 이유는 물가(건축비). 수요가 떠나는 곳은 못 따라간다 — 결국 땅의 가치 [▶ 언젠가는 옵니다 4:05](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=245), [4:25](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=265) | 📖 p.108~110, p.360 | A6 실질가격 |

## 2. 국면·추세·과열

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| C1 | **상승 순서**: 상급지 → 서울·경기 인기지역(마포·성동·과천·강동·동작·분당·영등포) → 외곽·구축 | [▶ 지금 팔고 하락장 기다릴까 0:46](https://www.youtube.com/watch?v=HWJULtSpT7w&t=46). 하락 뒤 반등도 선호 지역·절대 금액이 많이 빠진 고가부터 [▶ 오를까 내릴까 5:15](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=315), [5:41](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=341) | 📖 p.111 | B5 |. 백테스트 2026-11-28(서울 84㎡ 2021~26, 금액대 6구간): 급지 사이 '고가부터' 순서는 뚜렷하지 않음 — 22년 하락은 9~15억이 먼저(22.01), 24년은 하락·반등 모두 거의 같은 달, 26년 3~4월 25억+ 조정은 아래로 안 번짐. 반등 폭은 고가가 큼(24.05 30억+ +5.9% vs 9~12억 +1.6%)
| C2 | **과열 = 범위의 문제.** 얼마나 올랐나가 아니라 어디까지 올랐나. 기피하던 외곽·나홀로("립밤 아파트")까지 오르면 거품, 매수 멈추고 관망 | [▶ 지금 팔고 하락장 기다릴까 1:32](https://www.youtube.com/watch?v=HWJULtSpT7w&t=92) | 📖 **p.111~114**, p.128 | B5 과열 확산도 |
| C3 | 하락은 **과열 위에 트리거**(2021년엔 금리)가 더해질 때 | [▶ 지금 팔고 하락장 기다릴까 3:03](https://www.youtube.com/watch?v=HWJULtSpT7w&t=183). 전제는 시세가 비싼 것 — 안 오른 곳은 금리가 올라도 안 떨어진다 [▶ 오를까 내릴까 3:12](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=192), [3:18](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=198) | 📖 p.48~49 | B5 + G3·G4 |
| C4 | **추세는 최소 1년.** 1년 오르면 상승장, 1년 변화 없으면 보합장, 1년 내리면 하락장. 3개월 반짝은 "잠깐 반등" | – | 📖 **p.136** | B1 국면 라벨 |
| C5 | **단기 조정 vs 대세 하락.** 조정은 일부 지역·짧게·5~10%에서 멈춤. 대세 하락은 경기침체·구조조정, 전국 동반, **전세도 함께 무너짐**. 대세 하락이면 **고점 대비 20%**에서 매수 | [▶ 드디어...시작인가 3:49](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=229) | 📖 **p.434~436, p.443~444** | B3 낙폭, B4 하락 분류 |
| C6 | **전고점 회복 3패턴**: 회복 지연(사면 안 됨) / 순조로운 회복(상승 여력 있음) / 신고가 돌파(상급지). 반등장은 아무 자산이나 끌어올리지 않는다 | [▶ 더 떨어질까요?? 2:17](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=137) | 📖 **p.280~282** | B2 회복 패턴 |
| C7 | **2023년 초 대비 반등하지 않은 아파트는 주의** | [▶ 더 떨어질까요?? 4:34](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=274), [▶ 경기 외곽까지 번질 겁니다 52:10](https://www.youtube.com/watch?v=GZfTpovi56k&t=3130), [1:08:43](https://www.youtube.com/watch?v=GZfTpovi56k&t=4123) (부읽남TV 출연, B등급, 26-11-06 촬영) | 📖 p.115~116, p.282, p.285 | B2 |
| C8 | **시장의 본질은 상승이 아니라 상승의 차이.** 옆 지역·상위 입지보다 덜 오르면 한계 신호 | – | 📖 **p.420~421** | B6 상대강도 |
| C9 | 하락장은 자주 오지 않는다. 조정장·휴식장(보합)도 매수 타이밍 | [▶ 고점 물린건가요 2:18](https://www.youtube.com/watch?v=YaC1c9jhCfY&t=138) | 📖 p.114~115, p.162~163 | B1 |
| C10 | 큰 상승장 전에 크게 오를 자산을 **선점**. 조용할 때는 좋은 자산과 평범한 자산의 격차가 작다 | – | 📖 p.450~451 | E6 격차 축소 구간 |
| C11 | **상승장 끝물 신호 = 경기 완전 외곽과 오피스텔까지 들썩일 때.** 그때는 작은 트리거에도 분위기가 반전된다. 위치 좋은 곳의 5~6억대가 20평대(국평 7~8억 동네)면 괜찮고, **30평대가 5~6억인 곳까지 움직이면 주의** | [▶ 경기 외곽까지 번질 겁니다 34:40](https://www.youtube.com/watch?v=GZfTpovi56k&t=2080), [35:19](https://www.youtube.com/watch?v=GZfTpovi56k&t=2119), [55:53](https://www.youtube.com/watch?v=GZfTpovi56k&t=3353), [56:08](https://www.youtube.com/watch?v=GZfTpovi56k&t=3368) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | 시장 탭 과열신호 '경기 외곽 신고가'(indicators C11, 🔧 5% 주의·25% 끝물 백테스트). 오피스텔은 수집 안 함 |
| C12 | **상승률 비교는 최소 3년.** 지역마다, 같은 지역에서도 대장 단지부터 오르는 순서가 있고 키 맞추기를 한다. 6개월~1년 상승률만 보고 잘못 샀다고 판단하지 마라. 다만 **남들이 다시 오르는데 나만 못 오르면 그 아파트의 문제**(C8과 같은 맥락) | [▶ 언젠가는 옵니다 1:01](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=61), [1:21](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=81), [3:44](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=224). 비슷한 단지는 같은 흐름으로 간다(단거리가 아니라 중·장거리) [▶ 호가가 비쌀 때 2:27](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=147), [2:47](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=167) | – | B6-3y 3년 비교(구현 2026-11-28, 상세 '작가 기준 점검' + 이웃 단지 표) |. 백테스트 2026-11-28(서울·경기 생활권 262곳, 대장 = 가장 비싼 3곳): 같은 생활권 안에선 대장이 먼저인 경우가 더 많음(23년 반등 92:49, 24년 반등 99:79), 다만 평균 0.2~0.7개월 — 신고 기한 30일보다 짧아 미리 알기엔 짧음. 26년 조정은 차이 없음(34:33)

## 3. 거래량·환금성

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| V1 | **전체 거래량은 방향 지표가 아니다.** 단지 거래량(환금성)이 중요 | [▶ 너가 보고 있는 그 아파트 사지마 0:23](https://www.youtube.com/watch?v=ecFJjYanPmY&t=23) | 📖 **p.147~148** | 시장 거래량은 C1 현황판으로만 |
| V2 | **거래 감소 ≠ 가격 하락.** 매물이 잠기면 거래절벽 속 신고가 | [▶ 누구일까 2:11](https://www.youtube.com/watch?v=1O6OKFh9iD4&t=131), [▶ 결국 전국 상승장 오는건가 2:30](https://www.youtube.com/watch?v=ESeOyYlHi1Q&t=150) | 📖 p.147 | 하락 신호로 쓰지 않음 |
| V3 | 거래 없는 이유 구분: 수요 부족 vs 공급(세대수·매물) 부족 | [▶ 도대체 얼마야? 3:51](https://www.youtube.com/watch?v=QEg2JGLCADo&t=231) | 📖 p.472~473 | C6 거래 적은 이유 (C2 회전율 + 평형 구간 세대수) |
| V4 | **환금성은 하락장에서 증명된다.** 하락장에 거래가 많았던 단지 = 환금성 좋음 | [▶ 경기도 대단지 vs 서울 어중간한 2:11](https://www.youtube.com/watch?v=M2rwWVE9VwQ&t=131), [▶ 경기 외곽까지 번질 겁니다 1:00:42](https://www.youtube.com/watch?v=GZfTpovi56k&t=3642), [1:01:15](https://www.youtube.com/watch?v=GZfTpovi56k&t=3675) (부읽남TV 출연, B등급, 26-11-06 촬영). 환금성을 강조하는 이유 = 하락장에 갈아타기 위해 [▶ 너무 많이 올랐나 7:48](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=468), [▶ 언젠가는 옵니다 5:06](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=306) | 📖 **p.138~142**, p.440 | C3 하락기 회전율 |
| V5 | **적정 거래량 = 월 세대수의 0.5~0.8%** (1천 세대면 월 5~8건) | – | 📖 **p.137**, p.165 | C2 기준선 |
| V6 | 대단지(1천 세대+)는 시세가 투명하고 환금성이 좋다. 초고가 시장은 예외 | – | 📖 p.116~122 | 단지 세대수 표시, 초고가 분리 |
| V7 | 거래량은 많은데 덜 오른 곳 = 움직이기 시작하는 곳 | [▶ 다들 멀리 가버렸어 4:38](https://www.youtube.com/watch?v=idrOVp7D1GY&t=278) | – | ⚠️ C8과 긴장 관계 (아래 참고) |
| V8 | **최소 250세대.** 그보다 작으면 나홀로 아파트 느낌. 단 교통 좋은 곳에 소형 단지가 몰려 있으면(염창·양평·문래) 괜찮고, **대단지 바로 옆 소형 단지는 소외**된다 | [▶ 경기 외곽까지 번질 겁니다 42:56](https://www.youtube.com/watch?v=GZfTpovi56k&t=2576), [43:09](https://www.youtube.com/watch?v=GZfTpovi56k&t=2589), [43:37](https://www.youtube.com/watch?v=GZfTpovi56k&t=2617) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | 입지 사실표 '단지' 줄 참고(미구현) |
| V9 | **3억대는 7~8억대만큼 오르지 않고, 환금성이 더 좋아야 한다.** 내 집 마련 수요는 보통 5억부터라 3억대는 싸도 수요가 적다. 평소 거래가 잘 되는지 확인 | [▶ 나중에 시세차익 큰 곳 4:50](https://www.youtube.com/watch?v=9f7SKimLzQA&t=290), [5:10](https://www.youtube.com/watch?v=9f7SKimLzQA&t=310) | – | C2 환금성 해석 주석 |

## 4. 급지·갈아타기·상대가치

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| L1 | 시세는 **급지 사다리**로 연결 (잠실 → 올림픽파크포레온 → 고덕 → 미사 → 다산) | [▶ 집값은 반드시 떨어집니다 0:45](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=45) | 📖 p.358~359 (고덕자이 → 고덕그라시움 → 올림픽파크포레온 → 잠실엘스) | E3 |
| L2 | **내 아파트의 미래 시세 = 바로 위 급지 단지의 현재 시세.** 단 생활권을 실제로 공유하는 단지와 비교 (연신내 ↔ 삼성동은 과도, 녹번·홍제·무악재가 적절) | – | 📖 **p.358~359, p.362**. 사다리 예: 고덕자이 → 고덕그라시움 → 올림픽파크포레온 → 잠실엘스, 과도한 예: 연신내 ↔ 삼성동 힐스테이트(GTX) 📖 p.358~359 (쪽수는 사용자 제공 책 요약 2026-11-28, 원문 대조 전) | E3 비교 단지 |
| L3 | **수익률이 아니라 절대 금액 격차.** 하락장엔 비싼 게 더 크게 빠져 격차가 좁혀진다 | [▶ 집은 반드시 떨어집니다 1:31](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=91). 비율은 비슷하게 빠져도 절대 금액이 커 보여 반등 때 먼저 산다 [▶ 오를까 내릴까 5:41](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=341) | 📖 p.301~303, **p.418~420** | E6 |
| L4 | **갈아타기는 최소 1.5배.** 1.2배는 거래비용으로 상쇄되는 돈 낭비. 같은 단지·동네 수평 이동 금지 | [▶ 갭투자 전면 금지 3:48](https://www.youtube.com/watch?v=1LNFc8iMQFM&t=228) | 📖 **p.436~438**, p.444, p.467 | E6 필터 |
| L5 | **갈아타기 타이밍 = 격차가 줄어든 때.** 상승 초반엔 고가가 먼저 올라 격차가 벌어지고 후반에 다시 좁혀진다 | [▶ 듣기만 하세요 4:36](https://www.youtube.com/watch?v=OXh7Cj_HUhM&t=276). 하락장에 내 집 −2억·상급지 −3억이면 기회, 상승장에 격차가 7억→5억으로 줄면 검토(벌어지면 오히려 비용 증가) [▶ 너무 많이 올랐나 7:28](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=448), [8:30](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=510) | 📖 **p.438~439**, p.265~266 | E6 격차 분위 |
| L6 | 초고가 시장(반포·압구정·한남)은 별개로 본다 | [▶ 반등의 속도가 너무 빠르다 0:36](https://www.youtube.com/watch?v=3T1QEM3mQ2A&t=36) | 📖 p.122 | 초고가 단지 분리 (구현 2026-10-18: 84㎡ 기준 시세 30억+ 를 '초고가'로 표시, 가격대별 흐름에서 따로) |
| L7 | **주변 시세가 높은 곳이 상승 여력이 크다** (같은 10억이라도 주변이 12~14억인 지역) | – | 📖 **p.216~217**, p.326, p.339, p.342 | E2 주변 시세 위치 |
| L8 | **한계 시세**: 하급지 84㎡ 천장 = 상급지 59㎡ 가격. 상급지가 오르면 천장도 오른다 | – | 📖 **p.217~219, p.228** | E4 |
| L9 | 가격대별로 다른 시장 (고가 꺾임, 저가 상승, 중간 숨고르기) | [▶ 금리상승의 후폭풍 4:36](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=276) | 📖 p.152 | 가격대별 지표 분리 (구현 2026-10-18 jobs/market.py price_bands: 84㎡ 환산 6/9/15/25/30억 구간별 B1 12개월 변화 중앙값, `market_signals.l9_price_bands`. 2026-10 서울 9~15억 +22.1%·30억+ +5.0%) |
| L10 | **지역 묶음(생활권)**으로 움직인다. 같은 묶음이면 시세 차이를 유지하며 함께 오르내린다 | "내 아파트만 안 오른다"면 몇 년 전 가격 차이(예: 2억)가 지금도 유지되는지 보라 — 유지되면 뒤처진 게 아니다 [▶ 호가가 비쌀 때 3:08](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=188), [3:28](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=208) | 📖 **p.468~470**, p.123~125 | 생활권 클러스터 정의 |
| L11 | **상급지 기준**: 주변 시세 15억 이상(평당 5천만 원 이상) 핵심 입지 | – | 📖 p.396 | E1 급지 컷오프 |
| L12 | 대형 평형 평당가는 눌린다. 비싼 지역일수록 소형·대형 평당가가 비슷. 최상급지가 아니면 40평대까지가 환금성 | – | 📖 p.247~250, p.468 | E5 |
| L13 | **비슷한 급지끼리 옮기는 건 의미 없다.** 내 지역이 유난히 안 오르면 잘 오르는 지역으로 같은 금액을 옮기는 건 괜찮다(L4 보완) | [▶ 경기 외곽까지 번질 겁니다 17:05](https://www.youtube.com/watch?v=GZfTpovi56k&t=1025), [17:24](https://www.youtube.com/watch?v=GZfTpovi56k&t=1044) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | L4 |
| L14 | **살 수 있는 것 중 가장 비싼 것, 건물값이 아니라 땅값이 비싼 곳을 사라.** 보통 비싼 게 더 오른다. 같은 돈이면 더 멀리(비규제) 나가지 말고 안쪽으로. 같은 8억이면 경기 신축보다 서울 구축(땅값은 거짓말하지 않는다), 다만 같은 가격의 신축·구축은 상품 비교 | [▶ 경기 외곽까지 번질 겁니다 25:38](https://www.youtube.com/watch?v=GZfTpovi56k&t=1538), [26:48](https://www.youtube.com/watch?v=GZfTpovi56k&t=1608), [29:04](https://www.youtube.com/watch?v=GZfTpovi56k&t=1744), [1:06:10](https://www.youtube.com/watch?v=GZfTpovi56k&t=3970), [1:06:45](https://www.youtube.com/watch?v=GZfTpovi56k&t=4005) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | 예산 안 후보 정렬 참고 |
| L15 | **저평가 ≠ 싼 것.** 좋은 자산이 일시적으로 할인된 게 저평가, 원래 안 좋은 게 저렴한 건 싼 것. **싼 곳의 공통점**: 도심과 절대거리가 멀다(택시비·막차), 세대수가 너무 적다, 지하철 없이 교통이 애매하다 | [▶ 경기 외곽까지 번질 겁니다 36:11](https://www.youtube.com/watch?v=GZfTpovi56k&t=2171), [36:16](https://www.youtube.com/watch?v=GZfTpovi56k&t=2176), [50:18](https://www.youtube.com/watch?v=GZfTpovi56k&t=3018) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | D1, V8 |
| L16 | **호가가 너무 비싸면 같은 생활권 대체 단지를 본다.** 싼 곳이 아니라 생활권이 겹치고 같은 입지·상품성으로 인식되는 곳(관악드림타운 → 벽산블루밍·우성, 행당한진 → 행당대림 → 왕십리풍림아이원·행당신동아, 철산주공13 → 12단지). 평소 같이 오르내렸는지, 지금만 싼지 확인. **1등 아파트를 살 필요는 없다** — 대출이 과해지거나 비싼 호가를 잡으면 나쁜 선택, 1등을 잘 따라가는 단지를 합리적 가격에 사면 좋은 선택 | [▶ 호가가 비쌀 때 1:05](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=65), [1:25](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=85), [1:46](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=106), [2:06](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=126), [5:11](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=311) | 📖 p.469: 마포프레스티지자이가 부담되면 같은 생활권 마포래미안푸르지오·공덕자이 (쪽수는 사용자 제공 책 요약 2026-11-28, 원문 대조 전) | 상세 '작가 기준 점검' 이웃 단지 3년 표(B6-3y, 2026-11-28) |
| L17 | **똘똘한 한 채 최소 기준 = 마포·성동·동작·강동·용산 대장급 59㎡.** 갈아타기로 도달할 목표 수준. 예: 마포래미안푸르지오, 래미안옥수리버젠, 흑석(리버파크)자이, 고덕그라시움, 이촌 한가람. 선호도 높은 주상복합(목동 하이페리온·갤러리아포레·타워팰리스)은 입지·상징성으로 거래가 수월한 예외(p.254~255) | – | 📖 **p.264**, p.254~255 (쪽수는 사용자 제공 책 요약 2026-11-28, 원문 대조 전) | 시장 탭 흐름 ① '작가가 꼽은 단지'(시안 2026-11-28: 59㎡ 20.7~23.8억) |

## 5. 전세·월세

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| J1 | 전세가율보다 **실거래 전세가와 매매가 자체**의 흐름 | [▶ 요즘 전세가는 거품인가 0:42](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=42) | 📖 p.148 (전세가 = 실거주 가치) | D2 |
| J2 | **4분면**: 매매↓전세↑ = 갭이 가장 좁혀지는 부의 사다리 기회 | [▶ 요즘 전세가는 거품인가 1:35](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=95) | – | D2 |
| J3 | **가격대별 전세가율 정상 범위**: 20억+ 30~50%, 8~15억 50~60%, 5억 이하 60~90%. 신축 높고 구축 낮음 | – | 📖 **p.148~152** | D1 |
| J4 | 전세가율 80~90%는 조심. 시장 평균 60% 균형, 50% 이하면 투자 수요 유입 어려움 | [▶ 요즘 전세가는 거품인가 3:55](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=235), [▶ 너무 빨리 오르고 있어요 3:49](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=229) | 📖 p.151 | D1 |
| J5 | **전월세 부족 → 매매 전환**이 집값을 자극. 학군지는 하락장에도 전세가 높아 매매를 받친다 | [▶ 재건축의 본질 0:00](https://www.youtube.com/watch?v=mVNPJeYbGU0&t=0), [▶ 전세의 종말 3:49](https://www.youtube.com/watch?v=erD3LizgYJo&t=229) | 📖 p.92~93 | D5 |
| J6 | **전세가 하락 원인 두 가지**: 주변 신규 입주, 매매가 하락. 20~30% 하락은 쉽지 않다. 역전세 대비 **전세가의 10%** 현금 | – | 📖 **p.153~154**, p.423 | D3, D4 |

## 6. 공급

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| S1 | **공급 효과는 지역마다 반대.** 대기 수요 많은 곳: 매매↑, 전세는 입주장(5~6개월)만↓, 2년 뒤↑. 대기 수요 적은 곳: 매매·전세 모두↓ | [▶ 상승여력 있는지 확인하는 법 3:06](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=186) | 📖 **p.54~56, p.63** | F1 |
| S2 | 신축이 지역 시세를 이끈다 (신축 → 준신축 → 구축 순) | – | 📖 p.56 | E7 |
| S3 | 공급 부족이라고 반드시 오르지 않는다 (심리적 저항선) | [▶ 너무 빨리 오르고 있어요 3:02](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=182) | 📖 p.53 | 단독 신호로 쓰지 않음 |
| S4 | **미분양은 원인을 봐라**: 분양가 과다 / 입지 / 상품성 / 공급 집중 / 거시. 가격 조정으로 풀릴 문제인지 구조적인지 | – | 📖 **p.155~160** | F3 |
| S5 | 2016년 이후 아파트는 지하주차장·커뮤니티가 표준이라 상품성이 쉽게 뒤처지지 않는다. 5~10년차에 "검증된 단지"로 재평가 | – | 📖 p.467~468 | 연식 구간 정의 |
| S6 | **공급보다 수요 변화가 중요.** 공급이 없어도 수요가 없으면 안 움직이고, 많아도 수요가 더 많으면 오른다. 지을 땅이 없어 못 짓는 것과 수요가 없어 안 짓는 것을 구분(대저택은 희소해도 안 오른다) | [▶ 고가는 꺾였고, 저가는 오르는 중 1:02](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=62), [2:24](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=144), [▶ 단독주택의 시대는 저물어가는가 1:02](https://www.youtube.com/watch?v=2VVIO2aepnc&t=62) | 📖 p.53 (S3) | 공급 지표 해석 주석 |

## 7. 금리·유동성·거시

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| R1 | 가장 강력한 힘은 **유동성**. 2005=100 기준 M2가 집값·소득보다 가파르다 | [▶ 금리상승의 후폭풍 0:00](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=0) | 📖 **p.50** | G1 |
| R2 | **금리는 집값을 조절하지 않는다.** 금리 인하는 경기가 나쁘다는 뜻일 수 있다 | – | 📖 **p.48~49** | G2 동행·역행 |
| R3 | 주담대 금리 **3~5%가 심리적 한계, 7%면 체감이 완전히 다르다** | [▶ 금리상승의 후폭풍 2:19](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=139) | – | G3 |
| R4 | 대출 **증가율 둔화**가 거래 감소로 이어진다 | [▶ 금리상승의 후폭풍 1:31](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=91) | – | G4 |
| R5 | 하락의 가장 큰 원인은 **소득 감소(실업률)**. **4% 접근 = 경기침체, 매매·전세 동반 하락. 6% 이상 = 경제 위기, 장기 불황** | [▶ 고점 물린건가요 3:05](https://www.youtube.com/watch?v=YaC1c9jhCfY&t=185) | 📖 **p.142~144** | G5 |
| R6 | **경매 낙찰가율**: 높으면 상승장 초입, 하락·보합장엔 하락. 아파트가 가장 정확 | – | 📖 **p.160~161** | G6 |
| R7 | 심리는 금리보다 강하지만, 소비심리지수는 객관성에 한계 | – | 📖 p.51~52 | G7 보조 |
| R8 | 고령화와 집값 하락은 직접 연관 없다 (의료·교통 때문에 수도권 잔류, 증여 자금 재유입) | – | 📖 p.399~400 | 인구 지표 해석 주석 |
| R9 | **인지도는 곧 수요.** 남들이 모르는 싼 아파트엔 이유가 있다 | – | 📖 p.401, p.409 | G7 검색량 → 단지 인지도 지수 `complex_search`(2026-10-19 코드, API HUB 앱에 검색어 트렌드 활성화 필요) |

## 8. 규제

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| G1 | 토허제는 거래를 줄여 상승 속도를 늦추지만 가격을 떨어뜨리진 않는다 | [▶ 결국 전국 상승장 오는건가 1:05](https://www.youtube.com/watch?v=ESeOyYlHi1Q&t=65) | 📖 p.269~270 | policy_events 마커 (구현 2026-10-18 collector/policy.py: 토허 구역 기간·규제지역 기간·사건 9건, 84㎡ 차트 표시, C4 해석 주석) |
| G2 | **풍선효과**: 규제 지역 밖의 비슷한 급지로 수요 이동 → 따라가지 마라 | [▶ 너무 높은 호가 따라가지마세요 3:19](https://www.youtube.com/watch?v=8SadWiCzQao&t=199) | 📖 **p.288~292** | 경계 인접 지역 상대 상승률 (구현 2026-10-18 jobs/balloon.py: 시군구 토허 확대일마다 새로 규제·붙은 바깥·먼 바깥의 R-ONE 주간 지수 누적 변화, 매입자 거주지 외지인·서울 비중 전후 6개월) |
| G3 | 규제 지정 = 정부도 수요가 강하다고 본 곳. 지정 여부로 우열을 판단하지 마라 | – | 📖 p.270, p.326 | 해석 주석 |
| G4 | **규제의 역설.** 투과지구·토허제로 재건축 조합설립 뒤 매물이 1/10로 줄고(조합원 지위 양도 제한), 세입자는 나가야 해 전월세도 줄어 **강제 매수** → 공급이 적은데 수요가 늘어 오른다. 규제는 하기 쉽고 풀기 어렵다. 정책은 바뀌어도 입지는 안 바뀐다 | [▶ 고가는 꺾였고, 저가는 오르는 중 1:43](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=103), [2:04](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=124), [2:46](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=166), [6:12](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=372) | – | J5·관심 지역 전세 표(#rentP) 해석 주석 |

## 9. 입지·호재·정비사업 (설명용)

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| D1 | 입지 = 업무지구·학군·상급지와의 **절대거리** | [▶ 경기 외곽까지 번질 겁니다 45:05](https://www.youtube.com/watch?v=GZfTpovi56k&t=2705), [50:18](https://www.youtube.com/watch?v=GZfTpovi56k&t=3018) (부읽남TV 출연, B등급, 26-11-06 촬영) | 📖 **p.85~103** | H2, H3, E8 상급지까지 거리 |
| D2 | **교통 호재는 중심업무지구(사대문·여의도·강남) 연결이 핵심.** GTX는 어디서 타는지가 아니라 **어디서 내리는지**. 외곽 순환·경전철은 약함 | [▶ 경기 외곽까지 번질 겁니다 44:36](https://www.youtube.com/watch?v=GZfTpovi56k&t=2676), [45:47](https://www.youtube.com/watch?v=GZfTpovi56k&t=2747), [51:02](https://www.youtube.com/watch?v=GZfTpovi56k&t=3062) (부읽남TV 출연, B등급, 26-11-06 촬영). 노선 개수보다 일자리와 얼마나 많이·빠르게 연결되나, 여러 업무지구로 갈 수 있나(확장성) [▶ 어떤 노선인지, 어디에 있는지가 더 중요합니다 3:06](https://www.youtube.com/watch?v=ytWGioUQpa0&t=186), [3:47](https://www.youtube.com/watch?v=ytWGioUQpa0&t=227) | 📖 **p.68~70, p.86~87** | H2 |
| D3 | 쇼핑몰·병원·대형마트·고속도로·IC·관광지·산업단지는 아파트 호재가 아니다 (급지를 바꾸는 종합 개발이면 예외) | [▶ 연장하세요 3:52](https://www.youtube.com/watch?v=yLZ7NHDCJek&t=232) | 📖 **p.74~75, p.277~278** | H4 가중치 0 |
| D4 | 지하철은 **착공 후 들어가도 늦지 않다.** 진짜 악재는 **사업 취소** (지연은 악재 아님) | – | 📖 **p.279~280, p.357~358** | H4 단계 |
| D5 | 역세권 = 평지 **700m·도보 10분**. 동선의 질(밝은 상권 vs 어두운 골목)이 중요 | – | 📖 **p.220~228** | H1 |
| D6 | 학군지는 구축인데도 전세가 높고 하락장에 강하다. 학령인구 감소로 **최상위 학군은 더 견고, 중간 학군은 약화** | [▶ 학생이 없어...... 2:22](https://www.youtube.com/watch?v=b533wvHHo3g&t=142), [6:37](https://www.youtube.com/watch?v=b533wvHHo3g&t=397) | 📖 p.89~95 | H3 (학원가 순위·학령인구. 학원 수만으로는 학군지를 못 가려 판정은 안 함) |
| D7 | 상승 여력 점검: 소득, 생산가능인구, 개선 가능성(재건축), 추가 공급 토지, 대체 불가성 | [▶ 상승여력 있는지 확인하는 법 0:47](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=47) | 📖 p.218~219 (한계 시세 = 주민 소득·자산) | H6 주민 소득, H3 생산가능인구, 입지 화면 점검표 |
| D8 | **재개발은 조합설립인가 이후** 매수. 노후도(30년+ 비율) 미충족이면 불가. 가장 큰 리스크는 시간 | [▶ 갭투자 전면 금지 18:37](https://www.youtube.com/watch?v=1LNFc8iMQFM&t=1117). 상승장엔 아파트 한 채가 재개발보다 더 오르고 갈아타기도 쉽지만, 완공되면 재개발이 더 비싸진다 [▶ 나중에 시세차익 큰 곳 3:27](https://www.youtube.com/watch?v=9f7SKimLzQA&t=207), [3:47](https://www.youtube.com/watch?v=9f7SKimLzQA&t=227) | 📖 **p.368~373** | H5 |
| D9 | **재건축 사업성**: 용적률 낮고 대지지분 크고 분양가 높고 일반분양 많을수록. 상급지는 절차 무관, 중·하급지는 조합설립인가 후. 기간 20~25년 | [▶ 재건축의 본질](https://www.youtube.com/watch?v=mVNPJeYbGU0) | 📖 **p.374~397** | H5 |
| D10 | 피해야 할 자산: 오피스텔, 재개발 안 되는 빌라, 지식산업센터, 분양형 호텔, 신축 상가, 지역주택조합 | – | 📖 p.408~409 | 분석 대상에서 제외 |
| D11 | **초기 재개발·초기 재건축 주의.** 재개발은 **최소 시공사 선정**은 된 곳(D8 조합설립인가보다 한 단계 뒤), 빌라 쪼개기·분담금 불확실. 재건축은 조합설립 뒤 10년 보유·5년 거주 요건에 묶일 수 있고 90년대 초 애매한 단지는 쉽지 않다. 속도 잘 나는 재개발은 옆 신축보다 아직 싸다 | [▶ 경기 외곽까지 번질 겁니다 13:22](https://www.youtube.com/watch?v=GZfTpovi56k&t=802), [13:36](https://www.youtube.com/watch?v=GZfTpovi56k&t=816), [18:20](https://www.youtube.com/watch?v=GZfTpovi56k&t=1100), [18:37](https://www.youtube.com/watch?v=GZfTpovi56k&t=1117), [19:27](https://www.youtube.com/watch?v=GZfTpovi56k&t=1167), [47:14](https://www.youtube.com/watch?v=GZfTpovi56k&t=2834) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | H5, 정비 진행 현황 |
| D12 | **재개발 밀집 지역 주변 구축·준신축은 개발 수혜**(노량진·광명). 교통 + 주변에 변화가 많은 곳 | [▶ 경기 외곽까지 번질 겁니다 28:11](https://www.youtube.com/watch?v=GZfTpovi56k&t=1691), [28:25](https://www.youtube.com/watch?v=GZfTpovi56k&t=1705), [28:34](https://www.youtube.com/watch?v=GZfTpovi56k&t=1714) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | 개발 호재·주변 정비사업 카드 |
| D13 | **리모델링 긍정적.** 방 2개·복도식·주차 불편이 확실히 개선되면 준신축처럼 바뀐다. 1세대 리모델링은 볼품없었지만 새로 완성되는 단지(분당 정자·이촌 르엘)가 좋으면 더 뜨거워질 것. 규제가 덜해 속도가 난다(수지·분당·수원). 공사비는 따져 볼 것 | [▶ 경기 외곽까지 번질 겁니다 48:54](https://www.youtube.com/watch?v=GZfTpovi56k&t=2934), [48:58](https://www.youtube.com/watch?v=GZfTpovi56k&t=2938), [49:15](https://www.youtube.com/watch?v=GZfTpovi56k&t=2955), [49:53](https://www.youtube.com/watch?v=GZfTpovi56k&t=2993) (부읽남TV 출연, B등급, 26-11-06 촬영). 분담금은 최소 3~5억, 가장 정확한 건 조합 사무실. 이주~입주 6~7년이라 3~4년 뒤 갈아탈 계획이면 일반 아파트가 낫다 [▶ 나중에 시세차익 큰 곳 2:25](https://www.youtube.com/watch?v=9f7SKimLzQA&t=145), [2:46](https://www.youtube.com/watch?v=9f7SKimLzQA&t=166) | – | 정비 진행 현황(리모델링) |
| D14 | **역세권은 노선 개수보다 역 위치와 노선의 힘.** 2·5호선 영등포구청 < 5호선 신금호, 4개 노선 수서 < 3호선 압구정 — 급지가 상위 개념(평당가·절대가로 객관화). **가격대가 낮을수록 역세권 비중이 크다: 10억 이하는 역까지 걸어갈 수 있는지가 중요**, 40~50억대는 환경·상품성·희소성. 도로·버스 등 대체 교통이 좋으면 역 거리 영향이 작아 도보 5분·15분 가격차가 지역마다 다르다 | [▶ 어떤 노선인지, 어디에 있는지가 더 중요합니다 0:22](https://www.youtube.com/watch?v=ytWGioUQpa0&t=22), [1:24](https://www.youtube.com/watch?v=ytWGioUQpa0&t=84), [2:04](https://www.youtube.com/watch?v=ytWGioUQpa0&t=124), [2:46](https://www.youtube.com/watch?v=ytWGioUQpa0&t=166), [4:29](https://www.youtube.com/watch?v=ytWGioUQpa0&t=269), [4:50](https://www.youtube.com/watch?v=ytWGioUQpa0&t=290) | 📖 p.220~228 (D5) | H1 역세권 해석 주석(가격대별 숫자 없음 → 판정 안 함) |
| D15 | **호재는 지금 입지에서 출발해 본다.** 지금 싼 이유가 지하철 없음 하나뿐이면 큰 의미, 직장 거리·주거 환경 등 약점이 여럿이면 역 하나로 안 풀린다. 새 노선은 어디로 가나·환승·배차·차량 수. 주변 재개발은 몇 m보다 동선(벽·큰 도로·경사·출입구)을 실제로 공유하는지. 신축이 들어오면 가격 상방은 올라가도 내 단지 약점은 그대로. 선반영은 비슷한 다른 지역과 비교. 가격이 비슷해졌다고 입지 역전은 아니다(연식·평형 차이일 수 있음). **원래 좋은 곳이 더 좋아진다** | [▶ 지하철 연장이 된다는데 집값은 그대로 1:23](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=83), [1:44](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=104), [3:30](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=210), [4:51](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=291), [5:33](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=333), [6:36](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=396), [7:16](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=436), [8:39](https://www.youtube.com/watch?v=H0pvMdt-0gA&t=519), [▶ 어떤 노선인지, 어디에 있는지가 더 중요합니다 4:50](https://www.youtube.com/watch?v=ytWGioUQpa0&t=290), [5:11](https://www.youtube.com/watch?v=ytWGioUQpa0&t=311) | – | 개발 호재 카드 해석 주석 |

## 10. 자금·실행

| # | 관점 | 유튜브 | 책 | 반영 |
|---|---|---|---|---|
| F1 | 매수 시점 = 사고 싶은 집을 살 돈이 있을 때. **종잣돈 + 최대 대출 = 볼 금액대** | [▶ 대출 막혔다고 기다리지 마세요 (지식인사이드 출연, B등급)](https://www.youtube.com/watch?v=56MQkUuS_dc), [▶ 경기 외곽까지 번질 겁니다 1:01:57](https://www.youtube.com/watch?v=GZfTpovi56k&t=3717), [1:02:20](https://www.youtube.com/watch?v=GZfTpovi56k&t=3740) (부읽남TV 출연, B등급, 26-11-06 촬영) | 📖 p.106~108, **p.295~298** | I1 |
| F2 | **거주·투자 분리** vs 실거주 월 지출 비교 (4.5%, 30년 원리금균등) | [▶ 드디어 집값 꺾이나 2:41](https://www.youtube.com/watch?v=FMa_9CXEF2U&t=161) | 📖 **p.33~44**, p.325 | I2 |
| F3 | 원리금 상환은 **세후 소득의 30%**가 마지노선 | – | 📖 **p.474** | I1 |
| F4 | 부대비용: 취득세·중개보수(8억 상한 0.4%)·법무사·이사·수리. 인테리어는 **집값의 최대 5%** | 구축은 확장·샤시·수리 상태로 몇 천만 원 차이 — 3천 싼 미수리 매물도 요즘은 조금만 고쳐도 5천. 수리비 협상은 지금 같은 매물 부족 장엔 거의 안 되고 보합·하락장엔 된다 [▶ 호가가 비쌀 때 3:48](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=228), [4:09](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=249), [4:29](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=269), [4:50](https://www.youtube.com/watch?v=XZF4lUnY1GY&t=290) | 📖 p.241, p.351, p.361, p.426 | I1, I4 |
| F5 | 종잣돈 대비 소득이 높으면 최대 대출 실거주, 소득 대비 종잣돈이 많으면 전세 레버리지 | – | 📖 p.293~294 | I2 분기 |
| F6 | **임장 = 지도·데이터로 모르는 실제 생활환경 확인.** ① 역까지 출퇴근 시간대 실제 도보 시간, 역→집 동선(밝은 평지 vs 언덕·어두운 골목·유흥가) ② 단지 안: 쓰레기장 위치, 조경·청결, 경사, 산책로, 보차분리, 지하주차장·이중주차, 동별 조망 차이 ③ 모든 아파트엔 단점이 있다 — 환금성이 좋으면 수요가 몰리는 장점을 찾고 감내할 단점을 정한다 | – | 📖 **p.227~229** (사용자 제공 사진, 2026-10-21. 원문은 저장소에 두지 않음) | 시안 v2 관심 탭 임장 기록(동선·단지 안·정리) |
| F7 | **무주택자는 하락장을 기다리지 마라.** 기다린 하락이 원하는 가격까지 안 올 수 있고, 안 샀는데 오르는 게 최악. 하락장을 기다리는 건 갈아타는 1주택자만. 집값 하락은 무조건 온다는 걸 인정하고 장기 우상향을 믿고 사되, 하락장에도 팔리는(거래량 많은) 것을 | [▶ 경기 외곽까지 번질 겁니다 52:44](https://www.youtube.com/watch?v=GZfTpovi56k&t=3164), [53:04](https://www.youtube.com/watch?v=GZfTpovi56k&t=3184), [53:16](https://www.youtube.com/watch?v=GZfTpovi56k&t=3196), [1:08:25](https://www.youtube.com/watch?v=GZfTpovi56k&t=4105) (부읽남TV 출연, B등급, 26-11-06 촬영) · 11/27 영상에선 "무주택자가 기다리는 건 개인 선택, **유주택자가 팔고 기다리는 건 위험**"(하락장이 늦게 오거나 짧게 지나갈 수 있음) [▶ 오를까 내릴까 5:55](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=355), [5:59](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=359). 기다린 결과가 10억 → 14억 → 12억이면 싸게 산 게 아니다 [▶ 언젠가는 옵니다 1:41](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=101) | – | C9 |
| F8 | **청약**: 남들이 모르는 청약(나홀로·연습 삼아)은 하지 말고 정면 승부. 평소 운이 보통이면 청약만 기다리지 말고 내 집 마련 | [▶ 경기 외곽까지 번질 겁니다 58:10](https://www.youtube.com/watch?v=GZfTpovi56k&t=3490), [58:35](https://www.youtube.com/watch?v=GZfTpovi56k&t=3515), [59:40](https://www.youtube.com/watch?v=GZfTpovi56k&t=3580) (부읽남TV 출연, B등급, 26-11-06 촬영) | – | – |
| F9 | **대응 원칙을 미리 적어 둔다.** 네 경우(안 샀는데 내림·오름, 샀는데 내림·오름)마다 할 일. 하락을 기다린다면 매수 기준(예: 고점 대비 20% — 숫자 자체는 의미 없고 사람마다 15~30%)과 그만큼 안 떨어질 때의 계획을 함께. 산 가격·예전 가격은 기준이 아니다. 적을 것: 산 이유, 얼마까지 떨어져도 보유, 언제 팔지, 어떤 조건이면 갈아탈지. 가장 위험한 건 기준 없이 예측만 하며 시간을 보내는 것 | [▶ 너무 많이 올랐나 1:21](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=81), [3:03](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=183), [3:24](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=204), [4:44](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=284), [7:07](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=427), [11:15](https://www.youtube.com/watch?v=_ySlz6d1kQU&t=675), [▶ 언젠가는 옵니다 5:48](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=348), [6:08](https://www.youtube.com/watch?v=WvB8peXZ3fs&t=368) | – | 계획 탭 '내 대응 원칙' 메모(구현 2026-11-28, v2-plan.resp 서버 저장) |
| F10 | **두 채 전략(혼인신고 전 각자 한 채, 여력 있을 때만)**: 다른 지역에(규제·상승 시기 분산, 단 둘 다 수요가 줄면 의미 없음), 한 채 대출이 크면 다른 한 채는 자기자본 위주, 단기는 비규제 아파트·장기는 재개발. 자금 출처를 분명히(증여세) | [▶ 자산을 제대로 불리고 싶다면 0:40](https://www.youtube.com/watch?v=vKLugnui6uY&t=40), [1:41](https://www.youtube.com/watch?v=vKLugnui6uY&t=101), [2:42](https://www.youtube.com/watch?v=vKLugnui6uY&t=162), [4:45](https://www.youtube.com/watch?v=vKLugnui6uY&t=285) | – | – |
| F11 | **1주택자의 레버리지: 내 집을 전세 주고 월세로 옮겨 투자금 만들기.** 전세금으로 대출을 갚고 남는 돈 + 현금(+ 상환 가능한 신용·회사 대출)으로 상급지 재개발·비규제 갭. 월세(주거비)를 낮게, 원리금·월세·생활비까지 계산. 젊을 때 추천, 실거주 안정을 택하는 것도 선택(작가 본인은 안 함) | [▶ 한 살이라도 젊을 때 해야 합니다 0:00](https://www.youtube.com/watch?v=BtnDMMXOjlo&t=0), [1:23](https://www.youtube.com/watch?v=BtnDMMXOjlo&t=83), [2:25](https://www.youtube.com/watch?v=BtnDMMXOjlo&t=145), [2:46](https://www.youtube.com/watch?v=BtnDMMXOjlo&t=166), [3:07](https://www.youtube.com/watch?v=BtnDMMXOjlo&t=187) | – | – |

---

## 유튜브와 책이 다르게 보이는 지점

| 쟁점 | 유튜브 | 책 | 분석기 처리 |
|---|---|---|---|
| 덜 오른 단지 | V7: 거래량 많은데 덜 오른 곳은 "이제 움직이기 시작하는 곳" | C8: 상승장에서 남들만큼 못 오르면 "한계 신호" | **상승장 초반에는 V7, 상승장이 1년 넘게 이어졌는데도 RS가 음수면 C8**로 해석. B1 국면과 B6 상대강도를 함께 표시하고, 거래 회전율이 높으면 V7 쪽 주석을 붙인다 |
| 전세가율 기준 | J4: 시장 평균 60% 균형 | J3: 가격대·연식별 범위 | 지역 평균에는 60%, 단지에는 가격대 범위 (D1) |
| 재개발 매수 시점 | D11: 최소 **시공사 선정**은 된 곳 ([부읽남 13:22](https://www.youtube.com/watch?v=GZfTpovi56k&t=802), 2026-11) | D8: **조합설립인가** 이후 (p.368~373) | 단계는 공공데이터 그대로 보여 주고 판정하지 않는다. 두 기준을 주석으로 함께 |
| 금리 | R3: 주담대 3~5%·7% 구간 | R2: 금리는 집값을 조절하지 않는다 | 금리는 **트리거 후보**로만 쓰고 단독 판정 금지. 과열 신호(B5)와 겹칠 때만 강조 |

---

## 시점 발언 (2026-11-06 촬영 · 부읽남TV, B등급)

그때 시장에 대한 판단이라 시간이 지나면 맞지 않을 수 있다(사용자 2026-11-15). 규칙·기준선으로 쓰지 않고, 그 시점 기록으로만 둔다.

| 발언 | 시점 |
|---|---|
| 정부의 집값 하락 경고는 현장에서 별로 느껴지지 않는다. 40억 이상 고가는 가성비 매물이 많고(55억 → 48억), 중가는 호가가 무섭게 오르고 매물마다 여러 팀이 본다 | [1:04](https://www.youtube.com/watch?v=GZfTpovi56k&t=64), [1:12](https://www.youtube.com/watch?v=GZfTpovi56k&t=72), [1:30](https://www.youtube.com/watch?v=GZfTpovi56k&t=90) |
| 마포·성동·동작·강동·과천·분당·영등포·서대문은 계속 가고, 노원·성북·강북은 더 뜨겁다 | [2:00](https://www.youtube.com/watch?v=GZfTpovi56k&t=120) |
| 압구정 등 초고가 20% 하락은 과하게 거래됐던 게 제값으로 온 것. 양도차익이 큰 오래된 보유자가 세금 때문에 내놓는 것이라 매물이 소화되면 다시 잠긴다 | [2:42](https://www.youtube.com/watch?v=GZfTpovi56k&t=162), [3:46](https://www.youtube.com/watch?v=GZfTpovi56k&t=226), [4:21](https://www.youtube.com/watch?v=GZfTpovi56k&t=261), [7:19](https://www.youtube.com/watch?v=GZfTpovi56k&t=439) |
| 강남 바로 밑(과천·분당·성동·동작·강동)이 거의 붙어 있어 강남이 더 내려가기 어렵다 | [5:40](https://www.youtube.com/watch?v=GZfTpovi56k&t=340) |
| 강남 바로 아래 급지의 현금 여력 있는 사람에게는 지금이 갈아타기 기회. 대출이 막혀 대부분은 어렵다. 반포 청약 결과를 기다리는 대기 수요가 많다 | [8:58](https://www.youtube.com/watch?v=GZfTpovi56k&t=538), [11:15](https://www.youtube.com/watch?v=GZfTpovi56k&t=675), [11:21](https://www.youtube.com/watch?v=GZfTpovi56k&t=681) |
| 10억대 경기 → 서울 갈아타기는 15~25억 구간이 안 눌려 어렵다. 토허제로 갭투자가 막혀 상급지 재개발을 권한다 | [12:44](https://www.youtube.com/watch?v=GZfTpovi56k&t=764), [12:51](https://www.youtube.com/watch?v=GZfTpovi56k&t=771) |
| 경기 남부가 반도체 성과급 등으로 많이 올라 서울이 덜 올랐다. 성과급 돈도 강동·송파·위례·동작까지 본다(경기 남부만 보는 건 과한 기대) | [19:50](https://www.youtube.com/watch?v=GZfTpovi56k&t=1190), [37:06](https://www.youtube.com/watch?v=GZfTpovi56k&t=2226) |
| 추가 대출 규제는 어렵다고 본다. 한다면 비규제 지역을 규제로 묶는 정도. 토허제는 당분간 안 풀 것 | [20:25](https://www.youtube.com/watch?v=GZfTpovi56k&t=1225), [21:15](https://www.youtube.com/watch?v=GZfTpovi56k&t=1275), [30:56](https://www.youtube.com/watch?v=GZfTpovi56k&t=1856) |
| 지금의 저평가는 초고가(강남)뿐, 나머지는 일반 시세, 과열된 곳은 딱히 없다 | [36:43](https://www.youtube.com/watch?v=GZfTpovi56k&t=2203), [36:57](https://www.youtube.com/watch?v=GZfTpovi56k&t=2217) |
| 상승장 중후반, 후반은 아니다(경기 완전 외곽이 아직 안 들썩임). 전월세가 없어 강제 매수로 돌아서 저가 시장도 나중엔 들썩일 것 | [34:36](https://www.youtube.com/watch?v=GZfTpovi56k&t=2076), [34:57](https://www.youtube.com/watch?v=GZfTpovi56k&t=2097) |
| 연말·연초 쉬었다가 성과급이 나오는 2~3월쯤 다시 반등하는 흐름. 지금은 쉬는 구간이라 괜찮은 매물이 가끔 나온다 | [40:58](https://www.youtube.com/watch?v=GZfTpovi56k&t=2458), [41:30](https://www.youtube.com/watch?v=GZfTpovi56k&t=2490) |
| 현금 1억 5천이면 생애최초로 5~6억대(노원·수원·산본) 사도 괜찮다 | [55:19](https://www.youtube.com/watch?v=GZfTpovi56k&t=3319), [55:40](https://www.youtube.com/watch?v=GZfTpovi56k&t=3340) |
| 금리는 과거처럼 급등하는 시장이 아니라 대비 가능. 하락 트리거는 이상한 것까지 다 오른 뒤 대량 해고·실적 감소·성장률 둔화 같은 뉴스 | [1:03:30](https://www.youtube.com/watch?v=GZfTpovi56k&t=3810), [1:03:52](https://www.youtube.com/watch?v=GZfTpovi56k&t=3832) |

## 시점 발언 (2026-11 · 작가 송희구 채널)

위와 같이 그때 시장 판단이라 규칙·기준선으로 쓰지 않는다. 11/27 = [▶ 오를까 내릴까](https://www.youtube.com/watch?v=U_ZpiuyXNdY), 11/12 = [▶ 고가는 꺾였고, 저가는 오르는 중](https://www.youtube.com/watch?v=L0LKvj7tbbg)

| 발언 | 시점 |
|---|---|
| **11/12** 초고가는 양도세 때문에 꺾였지만, 수요가 가장 많은 5~15억은 집 하나 보려면 몇 팀이 가고 호가는 비싸고 매물이 없다 | [1:22](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=82) |
| **11/12** 규제를 조금 푼다면 대출은 안 풀고(통화량, 사내대출도 규제), 재건축 조합원 지위 양도 조건은 풀 수 있다 — 매물이 나와 상승에 브레이크 | [3:46](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=226), [4:07](https://www.youtube.com/watch?v=L0LKvj7tbbg&t=247) |
| **11/27** 30억 넘는 시장은 확실히 꺾였고, 재건축 앞둔 단지가 신축보다 더 꺾였다(재초환·양도세 부담에 오래 보유한 사람이 매물을 냄 — 세금 정책이 먹힘) | [1:41](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=101), [1:50](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=110) |
| **11/27** 마포·성동·동작·영등포·강동·과천·분당·서대문, 마곡·용산·송파 비잠실·위례 등도 호가가 조금 내려간 매물이 보인다(실거래 19억이면 호가 20억부터 → 이제 18.5억, 싸게는 18억). 다만 완전한 하락세가 아니라 늘 있던 쉬어가는 장 | [2:35](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=155), [2:48](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=168), [2:57](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=177) |
| **11/27** 하락 트리거 예시: AI 열풍이 식어 반도체(삼성·하이닉스)·전력기기 수출이 꺾이고 협력사·고용으로 번지는 경우. 예측한 위기는 위기가 아니다 | [3:38](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=218) |
| **11/27** 10~15억은 보합(멈춤) → 이 구간 1주택자는 10억 후반대로 갈아타기 좋은 때. 10억 이하는 아주 뜨겁다(중고가에서 있던 일이 중저가로) | [4:31](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=271), [4:45](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=285), [4:52](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=292) |
| **11/27** 95주 연속 상승이지만 오른 곳만 올라 2021년처럼 전국 상승은 아니다(경기·서울 외곽은 그대로). 2023년 대비로는 많이 오른 건 사실 | [6:40](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=400), [6:54](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=414) |
| **11/27** 살 수 있는 것 중 가장 좋은 것을 사고, 예측보다 방향(갈아타기 계획)을 세워라 | [7:02](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=422), [7:08](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=428) |
| **11/27** 주가가 고점 대비 거의 반토막 → 주식 팔아 집 사려던 수요가 없어져 시장이 멈춘 이유 중 하나 | [7:38](https://www.youtube.com/watch?v=U_ZpiuyXNdY&t=458) |
