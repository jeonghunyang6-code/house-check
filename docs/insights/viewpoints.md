# 송희구 관점 카드 (A등급: 본인 유튜브 채널 `작가 송희구`)

- 수집: 2026-10-10, 채널 일반 영상 579개 중 자막 553개 (자동 자막)
- 방법: `tools/insight_crawler/triage.py`로 주제 키워드 구간을 추린 뒤 원문 맥락을 읽고 정리
- 표기: 관점은 요약이고, 「」 안은 자막 원문 일부. 링크는 해당 시점(`&t=초`)으로 이동
- 자동 자막이라 오인식이 있을 수 있음. 규칙으로 옮길 때 영상 해당 시점을 직접 확인한다

---

## 0. 메타 원칙 — 분석기의 성격을 정하는 관점

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| M1 | **예측하지 않는다.** 「매도 물량이 많으니까 떨어지고 … 금리가 낮으니까 올라가고 이런 무조건적인 규칙은 부동산 시장에서 적용이 되지 않습니다」 | 인사이트 계층은 "상승/하락 예측 점수"가 아니라 **과열·침체 관찰 체크리스트**로 만든다 | [집값의 방향은 어디로 1:32](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=92) |
| M2 | 고점·저점·트리거는 맞출 수 없고, **과열 정도는 관찰로 판단 가능**하다 | 신호마다 "지금 어느 정도인가"를 보여주고, 판단은 사용자가 한다 | [지금 팔고 하락장 기다릴까 3:49](https://www.youtube.com/watch?v=HWJULtSpT7w&t=229), [6:52](https://www.youtube.com/watch?v=HWJULtSpT7w&t=412) |
| M3 | 통계는 기간·범위에 따라 결과가 바뀐다 | 모든 지표에 기간·지역 범위를 명시하고 바꿔 볼 수 있게 한다 | [집값의 방향은 어디로 0:00](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=0) |
| M4 | 숫자보다 **현장 분위기**가 먼저 바뀐다 (중개소 분위기, 협상 가능 여부) | 데이터로 못 잡는 항목은 체크리스트에 "현장 확인" 칸으로 둔다 | [드디어...시작인가 7:39](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=459) |

## 1. 거래량 — ⚠️ 초기 설계 가정과 반대

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| V1 | 「대세 상승을 하려면 거래량이 뒷받침이 되어야 한다 … 저는 이 말에 동의하지 않습니다」. **전체 거래량은 의미 없고 해당 단지의 거래량이 중요** | 시장 전체 거래량을 상승·하락 신호로 쓰지 않는다. 거래량 화면은 "신고 지연 보정 현황판"으로 두고, **단지별 거래량**을 핵심 지표로 올린다 | [너가 보고 있는 그 아파트 사지마 0:23](https://www.youtube.com/watch?v=ecFJjYanPmY&t=23), [1:04](https://www.youtube.com/watch?v=ecFJjYanPmY&t=64) |
| V2 | **거래 감소 ≠ 가격 하락.** 매물이 잠기면 거래절벽 속에서도 신고가가 나온다 | "거래량↓ + 신고가 비중 유지"를 정상 패턴으로 분류 (하락 신호로 오판 금지) | [누구일까 2:11](https://www.youtube.com/watch?v=1O6OKFh9iD4&t=131), [결국 전국 상승장 오는건가 2:30](https://www.youtube.com/watch?v=ESeOyYlHi1Q&t=150), [듣다보면 부동산 공부가 33:44](https://www.youtube.com/watch?v=-EPgJ9bSXvA&t=2024) |
| V3 | 거래가 없는 이유를 구분: **수요 부족** vs **공급 부족**(해당 평형 세대수가 적거나 집주인이 안 팖) | 단지×평형별 "세대수 대비 거래 회전율"로 두 경우를 구분해 표시 | [도대체 얼마야? 3:51](https://www.youtube.com/watch?v=QEg2JGLCADo&t=231), [4:12](https://www.youtube.com/watch?v=QEg2JGLCADo&t=252), [서울 20평대 비교 2:49](https://www.youtube.com/watch?v=aacaTkfqXuQ&t=169) |
| V4 | **환금성** = 하락기에도 거래가 되는 단지. 「거래량도 별로 없고 상승도 아예 안 했다 이런 거는 … 빨리 매도」 | 단지 점수: ① 하락기(2022H2~2023초) 거래 유지율 ② 최근 상승률. 둘 다 낮으면 경고 | [경기도 대단지 vs 서울 어중간한 2:11](https://www.youtube.com/watch?v=M2rwWVE9VwQ&t=131), [PF 부실 위험 3:18](https://www.youtube.com/watch?v=3lxCtk1MVdQ&t=198), [지금 살까 말까 3:46](https://www.youtube.com/watch?v=DB2t56V_PfQ&t=226) |
| V5 | 거래량은 많은데 아직 덜 오른 곳 = 움직이기 시작하는 곳 | "거래량 상위 + 상승률 하위" 단지 목록 | [다들 멀리 가버렸어 4:38](https://www.youtube.com/watch?v=idrOVp7D1GY&t=278) |

## 2. 실거래가·호가 — 시세 판단 기준

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| P1 | **호가가 아니라 최근 1~2개월 실거래가**가 기준 | 단지×평형 "기준 시세" = 최근 60일 실거래 (1층 제외, 중층 이상 우선) | [요즘 호가 진짜 너무 합니다 1:33](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=93), [반등의 속도가 너무 빠르다 1:42](https://www.youtube.com/watch?v=3T1QEM3mQ2A&t=102) |
| P2 | 최근 실거래 대비 **3%까지는 설명 가능, 5% 넘으면 설명이 필요** (10억 → 10.3억 검토, 10.5억 안 삼) | 호가 입력 시 프리미엄 % 계산: ≤3% 녹색 / 3~5% 주의 / >5% 경고 | [요즘 호가 진짜 너무 합니다 1:56](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=116), [2:36](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=156), [5:02](https://www.youtube.com/watch?v=7VTlXM2j1bI&t=302) |
| P3 | 실거래 없는 평형은 **같은 단지 다른 평형**으로 보간 (같은 단지는 같은 폭으로 움직임), 그다음 **비슷한 급지 5개 단지** 비교 | 거래 없는 평형의 추정 시세 = 같은 단지 평형 간 보간, 비교 단지 5개 자동 추천 | [도대체 얼마야? 0:54](https://www.youtube.com/watch?v=QEg2JGLCADo&t=54), [1:10](https://www.youtube.com/watch?v=QEg2JGLCADo&t=70), [3:15](https://www.youtube.com/watch?v=QEg2JGLCADo&t=195) |
| P4 | **반등 신호**: 급매가 거래되면서 급매 수가 줄고 호가가 조금씩 오를 때. 급매가 많아지면 그건 급매가 아니라 시세 | (매물 데이터 필요) 실거래 하단 대비 호가 분포 추이 | [부동산 자산가들은 지금 3:28](https://www.youtube.com/watch?v=GUL2aBsyvBE&t=208), [3:53](https://www.youtube.com/watch?v=GUL2aBsyvBE&t=233), [하락하는 집값 1:25](https://www.youtube.com/watch?v=uxxxa0_EP_Y&t=85) |
| P5 | 매물 **수**보다 **호가 방향**과 집주인이 얼마나 급한지가 중요 | (매물 데이터 필요) 매물 수보다 "실거래 대비 호가 중앙값" 추이를 보여준다 | [집값의 방향은 어디로 0:45](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=45) |

## 3. 국면 — 과열과 하락 초입 체크리스트

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| C1 | **상승 순서**: 상급지 → 서울·경기 인기지역 → 신축·학군·재건축·교통 → 오래 지나 외곽·구축·공급 많던 지역 | 지역을 급지 단계로 묶고, 단계별 상승 시작 시점을 타임라인으로 표시 | [지금 팔고 하락장 기다릴까 0:46](https://www.youtube.com/watch?v=HWJULtSpT7w&t=46) |
| C2 | **끝물 신호**: 수요 약한 외곽·구축·공급 많던 곳까지 뛰고, 거래 없던 곳에서 신고가가 나오고, 지방 외곽 구축 거래가 활발해짐. 「모든 자산이 같은 방향으로 움직이는 시장은 오래 지속되기 어렵습니다」 | **과열 지표 1순위**: 하위 급지·구축 단지의 신고가 비중과 거래 증가율, 전체 지역 중 상승 지역 비율(확산도) | [지금 팔고 하락장 기다릴까 1:32](https://www.youtube.com/watch?v=HWJULtSpT7w&t=92), [3:49](https://www.youtube.com/watch?v=HWJULtSpT7w&t=229), [드디어 집값 꺾이나 7:41](https://www.youtube.com/watch?v=FMa_9CXEF2U&t=461) |
| C3 | 하락은 **과열 위에 트리거**(2021년엔 금리)가 더해질 때. 2021년은 전국 오버슈팅 | 과열 지표가 높을 때 금리·대출 지표 급변을 함께 강조 | [지금 팔고 하락장 기다릴까 3:03](https://www.youtube.com/watch?v=HWJULtSpT7w&t=183), [금리상승의 후폭풍 5:22](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=322) |
| C4 | 호가가 하루에 몇천~몇억씩 오르면 **쉬어가는 타이밍은 반드시 온다** (특히 15억 이상) | 단기 상승 속도(주간 변동률 가속도) 경고 | [너무 빨리 오르고 있어요 0:00](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=0), [0:45](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=45) |
| C5 | **하락장 초입**: 매도 매물 + **전세 매물까지 동시 증가**, 호가 내린 매물이 등장하고 협상이 가능해짐. 매도 매물만 늘고 전세가 부족하면 패닉 매도가 아님 | (매물 데이터 필요) 매매·전세 매물 수 동시 증가 여부 | [드디어...시작인가 2:16](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=136), [3:49](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=229), [6:07](https://www.youtube.com/watch?v=hK6_yDINMKQ&t=367) |
| C6 | 하락장은 다 같이 떨어지지만 **반등장은 아무 자산이나 끌어올리지 않는다** | 지난 하락·반등기의 단지별 회복률 표시 | [더 떨어질까요?? 2:17](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=137), [3:02](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=182) |
| C7 | 2023년 초 저점 대비 꾸준히 우상향했다면 상승 여력이 있는 단지 | 단지별 "2023-01 저점 대비 추세" 지표 | [더 떨어질까요?? 4:34](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=274), [고점 물린건가요 2:18](https://www.youtube.com/watch?v=YaC1c9jhCfY&t=138) |

## 4. 지역 간 연결 — 급지 사다리

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| L1 | 시세는 연결되어 있다: 잠실 → 올림픽파크포레온 → 고덕·상일·명일 → 하남 미사 → 다산. 비싸지면 바로 아래 급지로 수요 이동 | **급지 체인** 데이터 정의 → 상위 급지 상승 후 하위 급지 시차 반응 차트 | [집값은 반드시 떨어집니다 0:00](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=0), [0:45](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=45), [듣다보면 부동산 공부가 7:00](https://www.youtube.com/watch?v=-EPgJ9bSXvA&t=420) |
| L2 | 시차를 두고 움직이는 게 정상. 초고가(반포·압구정) 시장은 별개로 봐야 한다 | 초고가 단지는 체인 분석에서 분리 | [다들 멀리 가버렸어 4:59](https://www.youtube.com/watch?v=idrOVp7D1GY&t=299), [반등의 속도가 너무 빠르다 0:36](https://www.youtube.com/watch?v=3T1QEM3mQ2A&t=36) |
| L3 | 수익률(%)이 아니라 **절대 금액 격차**를 봐라. 갈아타기 = 격차 줄이기. 하락장에선 비싼 게 더 크게 빠진다 | "내 단지 ↔ 목표 단지" 격차(억 원) 추이 차트. 하락기 격차 축소 구간 표시 | [집값은 반드시 떨어집니다 1:31](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=91), [3:04](https://www.youtube.com/watch?v=aB-JqTJAm_U&t=184), [더 떨어질까요?? 5:20](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=320) |
| L4 | 갈아타기는 **최소 1.5배** 가격 단지로 | 갈아타기 후보 필터: 목표가 ≥ 현재가 × 1.5 | [갭투자 전면 금지 3:48](https://www.youtube.com/watch?v=1LNFc8iMQFM&t=228), [블루베리 회식 시간 19:35](https://www.youtube.com/watch?v=8QjF8MbRSbg&t=1175) |
| L5 | 가격대별로 다른 시장: 고가는 꺾이고 저가는 빠르게 오르고 중간은 숨고르기. 금액이 높을수록 후보가 줄어 매도자 우위 | 가격대(10억 이하 / 10~15억 / 15~25억 / 25억+)별 지표 분리 | [금리상승의 후폭풍 4:36](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=276), [너무 빨리 오르고 있어요 1:30](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=90), [집 주인들 다 던지는 중 1:18](https://www.youtube.com/watch?v=2-SztbUURHY&t=78) |

## 5. 전세·월세

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| J1 | 전세가율보다 **실거래에 찍힌 전세가와 매매가 자체**의 흐름을 본다 (전세가율은 분수라 해석이 엇갈림) | 단지 화면에 매매·전세 실거래 시계열을 나란히. 전세가율은 보조 지표 | [요즘 전세가는 거품인가 0:42](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=42), [4:21](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=261) |
| J2 | **4분면**: 매매↑전세↑ = 매수 욕구 최대 / 매매↑전세→ = 매수 부담 / **매매↓전세↑ = 갭이 가장 좁혀지는 시기, 부의 사다리 기회** | 지역·단지별 매매·전세 변동률 4분면 차트 | [요즘 전세가는 거품인가 1:35](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=95), [2:26](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=146) |
| J3 | 전세가율 80~90%대는 오히려 조심 | 전세가율 80% 이상 경고 | [요즘 전세가는 거품인가 3:55](https://www.youtube.com/watch?v=jaXDRObmNbQ&t=235) |
| J4 | 시장 전세가율 60%가 균형, 50% 이하면 투자 수요가 시장을 끌어올리기 어렵다 | 지역 전세가율 60%·50% 기준선 표시 | [너무 빨리 오르고 있어요 3:49](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=229), [4:35](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=275) |
| J5 | **전월세 매물 부족 → 매매 전환**이 집값을 자극 (토허제·실거주 의무·비거주 과세가 전월세 공급을 줄임) | 전월세 실거래 건수·가격 급등 + 매매 동반 상승 감지 | [재건축의 본질 0:00](https://www.youtube.com/watch?v=mVNPJeYbGU0&t=0), [전세의 종말 3:49](https://www.youtube.com/watch?v=erD3LizgYJo&t=229), [이렇게 되면 집값은 2:48](https://www.youtube.com/watch?v=_wkQnQO_pTA&t=168), [드디어 집값 꺾이나 4:35](https://www.youtube.com/watch?v=FMa_9CXEF2U&t=275) |

## 6. 금리·유동성·거시

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| R1 | 시장을 움직이는 가장 강력한 힘은 **유동성**, 금리는 그 일부. 방향이 바뀌는 순간엔 금융이 개입 | 시장지표 화면 최상단에 M2·가계대출·주담대 **증가율** | [금리상승의 후폭풍 0:00](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=0) |
| R2 | 대출 증가율이 줄면 거래가 줄어든다 (증가 자체보다 **증가율 둔화**를 봐라) | 가계대출·주담대 증가율의 방향 전환 표시 | [금리상승의 후폭풍 1:31](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=91) |
| R3 | 주담대 금리 **3~5%가 심리적 한계 구간**, 7%면 체감이 완전히 달라짐 | 주담대 금리 카드에 3/5/7% 구간 표시 | [금리상승의 후폭풍 2:19](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=139) |
| R4 | 방향 = **하락 압력**(금리·대출 규제) vs **상승 압력**(공급 부족·전월세 부족)의 기울기 | 홈 화면을 압력 저울 형태로 구성 | [금리상승의 후폭풍 3:51](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=231), [4:36](https://www.youtube.com/watch?v=qYZaT2lXdYc&t=276) |
| R5 | 하락의 가장 큰 원인은 **소득 감소**: 대기업 일반직원 감원 → 협력사 → 실업률. 자영업 폐업도 장기화되면 연결 | 시장지표에 **실업률·고용** 추가 (현 설계에 없음) | [고점 물린건가요 3:05](https://www.youtube.com/watch?v=YaC1c9jhCfY&t=185), [집값의 방향은 어디로 3:05](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=185) |
| R6 | 매도해서 생긴 돈이 다시 부동산으로 가는지 다른 자산으로 가는지 | (참고 지표) 증시 예탁금 등. 우선순위 낮음 | [집값의 방향은 어디로 1:32](https://www.youtube.com/watch?v=VcI0DyZ8kNc&t=92) |

## 7. 공급

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| S1 | **공급 효과는 지역마다 반대**: 경기 외곽·인천 일부처럼 개발 토지가 많은 곳은 공급이 많을수록 하락. 서울·서울 인접 경기는 정비사업 신축이라 오히려 상승 | 입주물량 지표를 "외곽 신규택지형"과 "도심 정비사업형"으로 나눠 해석 | [상승여력 있는지 확인하는 법 3:06](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=186), [3:51](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=231) |
| S2 | 인기 지역 대단지 입주 시 **전세가만 일시 하락**, 주변 대표 단지 매매가는 오히려 상승 (둔촌주공 사례). 지방은 입주가 많으면 매매·전세 모두 하락 | 입주 전후 주변 단지 매매·전세 반응 비교 | [듣기만 하세요 13:09](https://www.youtube.com/watch?v=OXh7Cj_HUhM&t=789), [13:36](https://www.youtube.com/watch?v=OXh7Cj_HUhM&t=816) |
| S3 | 주변 입주가 많으면 해당 권역 시세가 정체 (이문·휘경 입주 → 답십리) | 반경 내 입주 예정 물량 표시 | [다들 멀리 가버렸어 4:02](https://www.youtube.com/watch?v=idrOVp7D1GY&t=242) |
| S4 | 공급 부족이라고 반드시 오르지 않는다. 너무 비싸다는 **심리적 저항선**이 생기면 보합·조정 | 공급 부족 신호 단독으로 상승 판정하지 않음 | [너무 빨리 오르고 있어요 2:16](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=136), [3:02](https://www.youtube.com/watch?v=JH5-x6eBnzI&t=182) |

## 8. 규제

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| G1 | 토지거래허가구역은 **거래량을 급감**시켜 상승 속도를 늦추지만 가격을 떨어뜨리진 않음. 하방 경직, 거래절벽 속 신고가 | 토허제 지정일 마커를 모든 차트에 표시, 지정 전후 거래량·가격 비교 | [결국 전국 상승장 오는건가 1:05](https://www.youtube.com/watch?v=ESeOyYlHi1Q&t=65), [1:30](https://www.youtube.com/watch?v=ESeOyYlHi1Q&t=90) |
| G2 | **풍선효과**: 같이 움직이던 단지가 토허제 안/밖으로 갈리면 밖의 호가가 과열 → 따라가지 마라 | 토허제 경계 인접 지역의 상대 상승률 비교 | [너무 높은 호가 따라가지마세요 2:46](https://www.youtube.com/watch?v=8SadWiCzQao&t=166), [3:19](https://www.youtube.com/watch?v=8SadWiCzQao&t=199), [추격매수 조심 1:07](https://www.youtube.com/watch?v=2nuczC9dQrY&t=67), [드디어 집값 꺾이나 0:45](https://www.youtube.com/watch?v=FMa_9CXEF2U&t=45) |

## 9. 장기 수요 기반 (입지 분석 화면)

| # | 관점 | 분석기 반영 | 출처 |
|---|---|---|---|
| D1 | 상승 여력 점검 5가지: **소득**(더 높은 가격을 감당할 수요), **생산가능인구(20~50대)**, **개선 가능성**(재건축·리모델링), **추가 공급 가능 토지**, **대체 불가성**. 특정 호재 하나에만 의존하면 위험 | 입지 분석 화면의 점검표 항목으로 그대로 사용 | [상승여력 있는지 확인하는 법 0:47](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=47), [1:33](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=93), [2:19](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=139), [4:37](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=277), [5:22](https://www.youtube.com/watch?v=BMJEO02sOlQ&t=322) |
| D2 | 회복하는 자산: **대체 불가능한 입지**, 입지가 아쉬우면 **상품성**(신축 또는 신축 전환 가능), **두꺼운 수요층**(실거주+투자) | 단지 회복력 점수 구성 요소 | [더 떨어질까요?? 3:02](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=182), [3:48](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=228), [4:34](https://www.youtube.com/watch?v=kSKGLcWqr5s&t=274) |
| D3 | 쇼핑몰은 원래 호재가 아니다 (아무것도 없던 곳의 예외는 있음) | 입지 레이어 가중치: 쇼핑몰은 기본 0 | [연장하세요 3:52](https://www.youtube.com/watch?v=yLZ7NHDCJek&t=232) |

---

## 아직 안 읽은 범위

- 키워드 상위 영상 위주로 읽었다. 553개 전체를 읽은 것은 아니다.
- 남은 주제: 입지·호재(366개 영상), 상급지·양극화(315개)의 하위 영상, 재건축·재개발, 라이브 방송, 『나의 첫 번째 부동산 교과서』(책 PDF로 보강 예정)
