# house-check 아키텍처 설계

> 목표: 송희구 작가의 시세 해석 관점(거래량·신고가·유동성·공급을 함께 읽기)을
> 데이터로 자동화한 **수도권 아파트 시장 분석기**.
>
> 참고 화면: APTIE(오늘의 실거래 / 거래량 / 가격동향 / 시장지표 / 입지분석) 10장.

---

## 0. 설계 원칙

1. **미확정 숫자를 확정치처럼 비교하지 않는다.**
   실거래 신고 기한(계약 후 30일) 때문에 한 달 거래량은 최대 61일에 걸쳐 쌓인다.
   모든 거래량 비교는 "같은 신고 경과일" 기준으로 한다.
2. **등록일은 우리가 직접 만든다.**
   국토부 API에는 계약일만 있고 신고(등록)일이 없다. 매일 스냅샷을 떠서
   처음 나타난 날을 `first_seen_date`로 기록한다. 과거로 소급할 수 없으므로
   **수집기를 가장 먼저 가동**한다.
3. **지표와 해석을 분리한다.**
   수치 계산(분석 계층)과 "그래서 어떤 국면인가"라는 해석(인사이트 계층)을 나눠,
   해석 규칙을 코드 수정 없이 바꿀 수 있게 한다.
4. **지역 범위는 수도권(서울 25개 구 + 경기 + 인천)**, 서울부터 순차 확장.
5. **개인용 도구.** 로그인·다중 사용자·트래픽 대응은 만들지 않는다.
6. **API는 필요해지는 시점에 하나씩 연결한다.** 키가 없는 소스는 해당 기능을 끄고
   나머지는 동작하게 한다(소스별 어댑터 + `.env` 키 유무로 활성화).
7. **실거래가가 종합 점수다.** 입지 가중치 합산 점수는 만들지 않는다. 입지 요소는
   "왜 이 가격인가"를 설명하는 데만 쓴다 (작가: "최종 점수는 시장이 만든 실거래가", 책 p.356).
   단지 비교는 단일 점수 대신 **지표별 충족 여부를 나란히 놓은 후보 비교표**로 한다 ([PRODUCT_PLAN.md](PRODUCT_PLAN.md) 결정 1).
8. **실거래가·거래량·환금성을 교차 검증한다** (책 p.167). 모든 가격 지표에 거래 건수와 신뢰도를 붙인다.

---

## 1. 전체 구조

```
┌──────────────────────── 수집 계층 (batch, 스케줄 실행) ────────────────────────┐
│ [매일]  국토부 아파트 매매·전월세 실거래   → 스냅샷 비교 → 신규/해제 판정        │
│ [매일]  ECOS 환율·국고채,  FRED 미 국채·기준금리                                │
│ [매주]  한국부동산원 R-ONE 주간 매매·전세 지수 (목요일 발표, 월요일 기준)        │
│ [매월]  ECOS 기준금리·M2·CPI·주담대 금리 / KOSIS 인허가·착공·준공·인구            │
│ [매월]  건설공사비지수, PIR (KB·HF)  ※ API 없으면 엑셀 수동 적재                │
│ [수시]  입지 레이어: 철도·도로망 계획, 개발사업, 지하철역 (GeoJSON 수동 관리)     │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        ▼
┌──────────────────────── 저장 계층 (PostgreSQL + PostGIS) ──────────────────────┐
│ deals · deal_events · complexes · complex_area_highs · daily_registration       │
│ price_index_weekly · macro_series · regions · geo_layers · insights             │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        ▼
┌──────────────────────── 분석 계층 (지표 엔진, Python) ─────────────────────────┐
│ A. 실거래 분석   : 신고가 판정, 전고점 대비율, 상승액·상승률                     │
│ B. 거래량 분석   : 경과일 누적곡선, 전월 동시점 대비, 집계율, 최종치 추정         │
│ C. 가격 모멘텀   : 주간·연간 변동률, 연속 상승/하락 주수, 지역 순위              │
│ D. 매크로 요약   : 전월·전년 대비, 추세 방향, 다음 발표일                       │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        ▼
┌──────────────────────── 인사이트 계층 (규칙 엔진) ─────────────────────────────┐
│ rules/*.yaml  → 지역별 신호 점수 → 시장 국면 판정 → 해설 문장 생성             │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        ▼
┌──────────────────────── API / 화면 계층 ───────────────────────────────────────┐
│ Next.js (모바일 우선) · ECharts(차트·코로플레스 지도) · MapLibre GL(입지 지도)   │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 화면 구성 (IA)

| 탭 | 내용 | 주요 데이터 |
|---|---|---|
| **홈(체크리스트)** | 압력 저울(하락 압력 vs 상승 압력), 과열·하락 초입·상승 압력·구조 변화 체크리스트 (5.2) | insights |
| **단지 분석** | 기준 시세·신뢰도, 국면, 전고점 회복 패턴, 상대강도, 환금성, 전세가율 정상 범위, 주변 시세 위치, 바로 위 급지 목표 시세·한계 시세 (5.3) | deals, complexes, complex_metrics |
| **갈아타기·계산기** | 예산 → 살 수 있는 단지, 실거주 vs 거주·투자 분리, 갈아타기 격차 차트(1.5배 필터·격차 축소 구간) | complex_metrics |
| **오늘의 실거래** | 오늘 새로 등록된 거래 리스트, "오늘 나온 신고가 N건", 지역(시/구/동) 필터, 정렬(거래금액·상승액·상승률), 신고가만 보기, 카드별 전고점 대비율·가격 스파크라인 | deals, complex_area_highs |
| **거래량** | 월별 거래량 + 전월 동시점 대비, 신고 경과일 누적곡선(당월·전월·전전월), 일별 등록건수(요일 필터·고점/저점/평균), 연·월 테이블 | daily_registration |
| **가격 동향** | 구 단위 주간 변동률 지도(매매/전세, 부동산원/KB), 서울·수도권 연속 상승 주수, 주간·연간 순위표, 주차 선택 | price_index_weekly |
| **시장지표** | 유동성·금리·물가(기준금리 한/미/유, M2, 주담대·신용대출 금리, CPI·근원, 환율, 국고채 3/5/10Y·스프레드, 건설공사비지수, PIR) / 주택공급(인허가·착공·준공) / 인구구조(피라미드, 수도권 생산가능인구) | macro_series |
| **입지 분석** | 지도 레이어 칩: 가격·교통(국가철도망·도로망)·개발·환경·인구, 구역/노선 클릭 시 상세 | geo_layers |
| **최고가 순위** | 단지×평형별 최고가, 지역별 최고가 랭킹 | complex_area_highs |

커뮤니티 기능은 범위에서 제외한다.

---

## 3. 데이터 소스

| 영역 | 소스 | 주기 | 비고 |
|---|---|---|---|
| 아파트 매매 실거래 | 공공데이터포털 `국토교통부_아파트 매매 실거래가 상세 자료` | 매일 | 단지일련번호, 해제여부·해제사유발생일, 거래유형(중개/직거래) 포함 |
| 아파트 전월세 | 공공데이터포털 `국토교통부_아파트 전월세 실거래가 자료` | 매일 | 전세가율 계산용 |
| 주간 가격지수 | 한국부동산원 R-ONE 오픈API | 매주 | 시군구 단위 매매·전세 |
| 단지 기본정보 | 공공데이터포털 `국토교통부_공동주택 기본 정보` (K-apt) | 분기 | 세대수·사용승인일·주차대수 → 회전율(C2), 연식대(E7) |
| 분양정보 | 공공데이터포털 청약홈 분양정보 | 매주 | 입주예정월·분양가 → 입주 물량(F1), 미분양 원인(F3) |
| 건축물대장 | 공공데이터포털 건축HUB | 수시 | 재개발 구역 노후도(H5) |
| KB 시세 | KB부동산 데이터허브 | 매주 | 공식 API 없음 → 엑셀 적재 (2차) |
| 한국 금리·통화·물가·환율·국고채 | 한국은행 ECOS 오픈API | 일/월 | 기준금리, M2, 주담대·신용대출 금리, CPI, 원달러, 국고채 |
| 미국·유로 금리·M2 | FRED, ECB Data Portal | 일/월 | 비교용 |
| 인허가·착공·준공 | KOSIS / 국토교통 통계누리 | 월 | |
| 인구 | KOSIS (행안부 주민등록인구) | 월/연 | 연령별 인구 |
| 가계대출·주담대 잔액, 실업률 | ECOS / KOSIS | 월 | 증가율 둔화·소득 감소 신호 (R2, R5) |
| 매물·호가 대체 | 실거래 파생 지표 / R-ONE 수급지수 / 국토연 소비심리지수 / 네이버 데이터랩 검색 트렌드 | 일·주·월 | [LISTING_DATA.md](LISTING_DATA.md) |
| 건설공사비지수 | 한국건설기술연구원 | 월 | API 여부 확인 필요 |
| PIR | KB 데이터허브 / 주택금융공사 HOUSTAT | 분기 | 수동 적재 가능 |
| 지도·위성 | VWorld (국토부 공간정보) | – | 배경지도, 항공사진 |
| 철도·도로 계획 | 국가철도망·도로망 계획 고시 | 수시 | GeoJSON 수동 작성·관리 |

> 공공데이터포털 개발계정은 일일 호출 한도가 있다. 수도권 시군구(약 80개 코드) ×
> 2개월 × 매매·전월세 = 하루 300건 이상이므로 **운영계정 신청**을 전제로 한다.

---

## 4. 핵심 로직

### 4.1 일일 스냅샷과 등록일 (`first_seen_date`)

```
매일 06:00 KST
for 지역코드 in 수도권:
    for 계약월 in [당월, 전월]:          # 신고 기한상 이 두 달만 변동
        rows = API(지역코드, 계약월)     # 전체 페이지
        upsert deals by deal_key
          - 처음 본 키   → first_seen_date = 오늘, event = 'registered'
          - 해제로 바뀜  → cancelled_at = 오늘,     event = 'cancelled'
          - 값이 바뀜    → event = 'modified'
```

- `deal_key` = 단지일련번호 + 계약일 + 전용면적 + 층 + 거래금액 (API에 거래 고유 ID가 없음)
- 공휴일 다음 날은 신규 등록이 없다. 일별 등록건수는 **영업일 기준**으로 비교한다.
- 수집 첫날에는 이미 있는 거래가 전부 "신규"로 잡힌다. 그래서 첫 실행은 `bootstrap`
  모드로 돌려 `first_seen_date`를 NULL(미상)로 둔다.

### 4.2 거래량 시차 보정

- **신고 경과일** = `first_seen_date - 계약월 1일 + 1` (1–61일, 차트는 60일로 고정)
- **전월 동시점 대비** = 당월 경과일 *d*일차 누적 ÷ 전월 *d*일차 누적 − 1
- **집계율(%)** = 오늘 경과일 ÷ 61. 화면의 "집계중 17%"가 이 값이다.
- **최종치 추정** = 당월 *d*일차 누적 ÷ 과거 12개월 평균 "*d*일차 누적/최종치" 비율.
  누적이 쌓일수록 신뢰구간이 좁아지고, 화면에는 범위로 표시한다.

### 4.3 신고가 판정

- 비교 단위: **단지(단지일련번호) × 전용면적 그룹**(소수점 버림, 예: 84.91 → 84)
- `prev_high` = 이 거래 **이전 계약일**에 체결되고 해제되지 않은 거래 중 최고가
- 신고가 = `price > prev_high`
- 화면 표시값
  - 전고점 대비율 = `price / prev_high` (예: 19억 대비 96.84%)
  - 상승액 = `price - prev_high`
  - 상승률 = `price / prev_high - 1`
- **직거래**와 **이후 해제된 거래**는 기본적으로 전고점 산정에서 제외한다. 옵션으로 포함할 수 있다.
- "오늘 나온 신고가" = `first_seen_date = 오늘` 이면서 신고가인 거래

### 4.4 가격 모멘텀

- 주간·연간 변동률은 R-ONE 지수에서 계산한다.
- 연속 상승 주수 = 최신 주부터 거꾸로 세어 변동률이 0보다 큰 주의 연속 개수
  (서울 "88주 연속 상승")
- 지역 순위 = 주간 변동률 기준 정렬, 연간 변동률 병기

### 4.5 매크로 카드 공통 포맷

모든 지표를 같은 구조로 저장하고 같은 카드 컴포넌트로 그린다.

```
{ series_id, name, unit, value, as_of, change, change_basis('전월'|'전년동월'|'전일'),
  sub_values: [{label:'🇺🇸', value:4.00}, ...], next_release, history[] }
```

---

## 5. 인사이트 계층 (송희구 관점 체크리스트)

| 문서 | 내용 |
|---|---|
| [insights/viewpoints.md](insights/viewpoints.md) | 관점 카드 (유튜브 626개 자막 + 책 전권, 영상 시점·쪽수 출처) |
| [insights/indicators.md](insights/indicators.md) | 지표 구현 명세 (A~I군: 정의, 계산식, 기준선, 데이터, 화면) |
| [INSIGHT_SOURCES.md](INSIGHT_SOURCES.md) | 출처 등급 정책 |

### 5.1 관점 수집으로 바뀐 설계

| 초기 가정 | 바뀐 설계 | 근거 (관점 ID) |
|---|---|---|
| 지역 신호 점수 → 국면 **예측** | **과열·침체 관찰 체크리스트**. 판정은 사용자가 한다 | M1, M2 |
| 입지 점수표 | 만들지 않음. 실거래가가 종합 점수 | M3 |
| 시장 전체 거래량이 가격을 선행 | 전체 거래량은 신고 지연 보정 현황판으로만. **단지 환금성(하락기 회전율)**이 핵심 | V1, V2, V4, V5 |
| 거래량↓ = 하락 신호 | 하락은 **단기 조정(국지·5~10%) vs 대세 하락(전국·전세 동반·실업)**으로 분류 | C5 |
| 국면 = 주간 변동률 | **추세는 최소 1년 같은 방향**, 3개월은 일시 반등 | C4 |
| 과열 = 많이 오름 | **상승이 어디까지 퍼졌나** (하위 급지·구축·소단지 신고가) | C2 |
| 지역 단위 분석 | **단지 × 평형** 중심, 생활권 클러스터와 바로 위 급지로 연결 | P1, L2, L10 |
| 전세가율 단일 기준 | **가격대·연식별 정상 범위** | J3 |

### 5.2 홈 화면 체크리스트

"하락 압력 vs 상승 압력" 저울 한 장과 체크리스트 묶음으로 구성한다.
묶음별 지표는 [indicators.md 3절](insights/indicators.md#3-홈-화면-체크리스트-매핑)에 정의했다.

| 묶음 | 대표 지표 |
|---|---|
| 과열 신호 | B5 과열 확산도, B1 상승장 지속 기간 |
| 하락 초입·대세 하락 | B4 하락 분류, B3 낙폭(5/10/20%), G5 실업률(4/6%), G4 대출 증가율 둔화 |
| 반등 신호 | A4 급매 체결 비중(5%) 하락, R-ONE 매매수급지수 상승 전환 |
| 상승 압력 | D5 신규 전세 감소, F2 인허가·착공 감소, G1 유동성 |
| 구조 변화 | 토허제 지정·해제, 풍선효과 (policy_events) |

### 5.3 단지 분석 화면

관점의 절반 이상이 단지 단위다. 화면 구성은 indicators.md의 A·B·C·D·E군을 따른다.

- 기준 시세와 신뢰도 (A1, A2), 층 보정 전처리
- 국면 라벨, 전고점 회복 패턴, 고점 대비 낙폭, 상대강도 (B1, B2, B3, B6)
- 월 회전율 0.5~0.8% 기준선, 하락기 환금성 (C2, C3)
- 전세가율 vs 가격대 정상 범위, 역전세 위험 (D1, D3)
- 주변 시세 위치, 바로 위 급지 비교 단지와 목표 시세, 한계 시세 (E2, E3, E4)

### 5.4 규칙 파일 형식

```yaml
- id: B4_major_downturn
  group: 하락 초입·대세 하락
  viewpoint: C5                                   # viewpoints.md 카드 ID (필수)
  source: ["book:p.435", "https://www.youtube.com/watch?v=hK6_yDINMKQ&t=229"]
  conditions:                                     # 3개 중 2개 이상
    - decline_region_ratio_4w >= 0.70
    - capital_jeonse_down_weeks >= 8
    - unemployment_rate >= 4.0 or unemployment_3m_change >= 0.5
  min_true: 2
  message: "하락 지역이 전국으로 퍼지고 전세도 함께 내려갑니다. 작가는 이를 단기 조정이 아닌 대세 하락의 특징으로 봅니다."
```

- `viewpoint`·`source`가 없는 규칙은 로드하지 않는다.
- 기준선은 작가가 숫자를 말한 것(📖·▶)은 그대로, 나머지(🔧)는 2021 고점·2023 저점 구간으로 백테스트해 정한다.

### 5.5 데이터 공백

| 공백 | 영향 관점 | 대안 |
|---|---|---|
| 매물 수·호가 | P2 호가 3%/5%, 매물 동시 증가 | 실거래 파생 + 수급지수 기본, 네이버 소량 수집(사용자 PC) 선택 ([LISTING_DATA.md](LISTING_DATA.md) C1) |
| 경매 매각가율 | R6 | 지지옥션 보도 추출(유력) + 감평협회 매각 통계(월별 여부 확인 대기) ([AUCTION_DATA.md](AUCTION_DATA.md)) |
| 업무지구 대중교통 시간 | D2 | 역간 소요시간 공공데이터로 노선 그래프 직접 구성 (7단계) |

---

## 6. 데이터 모델 (요약)

```sql
regions(code PK, name, level['sido'|'sigungu'|'emd'], parent_code, geom)

complexes(apt_seq PK, name, region_code, emd_name, jibun, built_year, approval_date,
          households, parking_spaces, lat, lng, nearest_station, station_dist_m,
          cluster_id, tier)                          -- K-apt + 계산값 (E0, E1)

clusters(cluster_id PK, name, station_codes[], validated_at, corr_min)   -- 생활권 (E0)

complex_metrics(apt_seq, area_group, month, base_price_10k, confidence, phase,
                recovery_pattern, drawdown, rel_strength, turnover, downturn_turnover,
                jeonse_ratio, peer_position, upper_peer_apt_seq, ceiling_price_10k,
                PK(apt_seq, area_group, month))      -- indicators.md A~E군 월 산출물

presale(notice_id PK, region_code, name, households, supply_price_per_py, move_in_month)  -- 청약홈 (F1, F3)

deals(
  id PK, deal_key UNIQUE, apt_seq FK, region_code,
  contract_date, area_m2, area_group, floor, price_10k,
  deal_type['중개'|'직거래'], is_cancelled, cancel_date,
  first_seen_date NULL, last_seen_date,
  prev_high_10k, is_new_high                -- 판정 결과 캐시
)
deal_events(id, deal_id, event['registered'|'cancelled'|'modified'], event_date, payload)

complex_area_highs(apt_seq, area_group, high_price_10k, high_deal_id, updated_at,
                   PK(apt_seq, area_group))

daily_registration(snapshot_date, region_code, contract_month, elapsed_day,
                   new_count, cumulative_count, PK(snapshot_date, region_code, contract_month))

price_index_weekly(source['reb'|'kb'], kind['매매'|'전세'], region_code, week_date,
                   index_value, weekly_change, PK(source, kind, region_code, week_date))

macro_series(series_id, obs_date, value, PK(series_id, obs_date))
macro_series_meta(series_id PK, name, unit, source, frequency, next_release)

geo_layers(id, category['교통'|'개발'|'환경'|'인구'], name, status, geom, props JSONB)

policy_events(id, kind['토허제'|'대출규제'|'세제'], region_code, start_date, end_date, note)


insights(region_code, as_of, checklist JSONB, summary TEXT)   -- 규칙별 현재값·기준선·충족 여부
```

---

## 7. 기술 스택

| 계층 | 선택 | 이유 |
|---|---|---|
| 수집·분석 | Python 3.12, httpx, pandas, pydantic | 공공 API·시계열 처리에 적합 |
| 스케줄 | GitHub Actions cron (초기) → 필요 시 서버 cron | 서버 없이 시작 |
| DB | PostgreSQL + PostGIS (Supabase) | 공간 쿼리, 무료 등급으로 시작 |
| 화면 | Next.js(App Router) + TypeScript | 모바일 웹·SEO |
| 차트 | Apache ECharts | 누적곡선, 코로플레스 지도, dataZoom(일별 등록 차트 하단 슬라이더) |
| 입지 지도 | MapLibre GL + VWorld 타일 | 레이어 토글, 3D, 측정 |
| 배포 | Vercel(화면), Supabase(DB) | |

---

## 8. 디렉터리 구조 (계획)

```
house-check/
├── collector/                 # Python: 수집
│   ├── sources/               # molit.py, reb.py, ecos.py, fred.py, kosis.py
│   ├── snapshot.py            # 일일 스냅샷 비교 → deal_events
│   └── jobs/                  # daily.py, weekly.py, monthly.py
├── analytics/                 # Python: 지표 계산
│   ├── new_high.py            # 4.3 신고가
│   ├── volume.py              # 4.2 시차 보정
│   ├── momentum.py            # 4.4 연속 상승·순위
│   └── macro.py               # 4.5 카드 포맷
├── insight/                   # 규칙 엔진 + rules/*.yaml + 백테스트
├── tools/insight_crawler/     # 유튜브 자막 수집 (관점 출처 확보용)
├── db/migrations/             # SQL 스키마
├── web/                       # Next.js 화면
├── data/geo/                  # 시군구 GeoJSON, 철도·도로 계획 레이어
├── .github/workflows/         # daily/weekly/monthly cron
└── docs/
```

---

## 9. 단계별 로드맵

| 단계 | 범위 | 완료 기준 |
|---|---|---|
| **1. 수집기 가동** | 서울 매매·전월세 실거래 일일 스냅샷 + 과거 이력 적재(2020~), DB 스키마, cron | 매일 `first_seen_date`가 쌓임 |
| **2. 오늘의 실거래 + 단지 분석** | K-apt 단지 정보, 전처리(층 보정·직거래 제외), A군·B1~B3·C2~C4·D1~D3 지표, 생활권 클러스터·급지(E0~E4) | "오늘 나온 신고가 N건", 단지 화면 |
| **3. 거래량** | 경과일 누적곡선, 동시점 대비, 일별 등록건수 | 화면 2~5번 재현 |
| **4. 가격 동향** | R-ONE 주간 지수, 구 단위 지도, 연속 상승, 순위 | 화면 1번 재현 |
| **5. 시장지표** | ECOS·FRED·KOSIS 카드 10종 | 화면 7~9번 재현 |
| **6. 체크리스트 + 계산기** | 규칙 파일 로더, B4·B5·B6, 정책 이벤트, 🔧 기준선 백테스트, 예산·갈아타기 계산기(I군) | 홈 화면 압력 저울·체크리스트 |
| **7. 입지 분석** | MapLibre 레이어(교통·개발·환경·인구) | 화면 10번 재현 |
| **8. 확장** | 수도권 전체, 전세가율, KB 시세, 알림 | |

1단계는 데이터가 쌓이는 데 시간이 걸린다. 그러므로 **가장 먼저, 다른 단계와 병행해서** 진행한다.

---

## 10. 미결 사항

- [x] 송희구 작가 관점 1차 수집: 유튜브 자막 → [insights/viewpoints.md](insights/viewpoints.md)
- [x] 저서 『나의 첫 번째 부동산 교과서』 전권 반영 → 관점 카드 통합, [insights/indicators.md](insights/indicators.md) 지표 명세
- [ ] 매물·호가: 실거래 파생 + 공식 지표로 진행, 네이버 소량 수집(C) 여부 결정 대기 ([LISTING_DATA.md](LISTING_DATA.md))
- [x] 사용 범위: 개인용
- [ ] API 키: 단계별로 필요할 때 발급 (1단계는 공공데이터포털 실거래가 키 하나)
- [ ] 건설공사비지수·PIR의 API 제공 여부 확인
- [ ] 경매 매각가율: 계산·추출 모듈 완료, 감평협회 파일 샘플 확인과 NAVER 키 대기 ([AUCTION_DATA.md](AUCTION_DATA.md))
- [ ] 전월세 API의 계약구분·갱신요구권 필드명 확인 (D5)
