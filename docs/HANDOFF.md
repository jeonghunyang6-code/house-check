# 진행 현황과 인수인계 (2026-10-11 기준)

새 세션은 이 문서부터 읽고, **그다음 `docs/PRODUCT_PLAN.md`(사용자 상황·합의 결정·Supabase 설정·진행 트랙)를 읽는다.**
작업 브랜치는 세션 시스템이 지정한 것을 따른다. **세션마다 브랜치가 달라 작업이 흩어진 적이 있다** (`inspiring-bell`, `vigilant-fermi`, `festive-heisenberg`, `brave-lamport`).
새 세션은 시작할 때 `git fetch origin` 후 `git branch -r`로 다른 `claude/*` 브랜치에 더 새 커밋이 있는지 먼저 확인하고, 있으면 합친다.
2026-10-11 `brave-lamport` 세션에서 앞의 세 브랜치를 모두 합쳤다.

## 0. DB 연결: 해결됨 (2026-10-11)

사용자는 비개발자이므로 **설명은 쉽게, 짧게**. SQL을 직접 붙여넣게 하는 방식은 사용자가 거부함.

### 접속 방법 (이것만 쓴다)

이 환경은 웹(443)만 나가고 Postgres 포트(5432·6543)는 막혀 있다 → `psql`/`DATABASE_URL` 직접 접속은 **불가**.
대신 **Supabase 관리 API**로 SQL을 실행한다:

```
REF=<DATABASE_URL 사용자명 postgres.<ref> 에서 추출, 20자>
curl -X POST "https://api.supabase.com/v1/projects/$REF/database/query" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" -H "Content-Type: application/json" \
  --data '{"query": "select 1"}'
```

- 성공 시 HTTP 201 + JSON 배열. SQL 오류는 HTTP 400 + `message`.
- 토큰 권한은 Database Read-write만. 그래서 `GET /v1/projects`(목록)는 **403 projects_read가 정상**이다. 이걸 보고 토큰이 안 된다고 판단하지 말 것 (2026-10-11에 한 번 그렇게 오판함).
- 토큰·`DATABASE_URL` 값은 출력 금지. ref는 비밀이 아니지만 로그에 남길 필요 없다.
- SQL 본문은 `python3 -c 'json.dumps(...)'`로 만들어 `--data @파일`로 보낸다 (따옴표 깨짐 방지). 마이그레이션은 `begin; … commit;`으로 감싼다.

### 실제 DB 상태 (PostgreSQL 17.11, Supabase 서울)

| 마이그레이션 | 상태 |
|---|---|
| `0001_deals.sql` | **적용·검증 완료** — `deals`(17열), `deal_events` 생성, 인덱스 6개. 면적 자동 계산(84.97→84), 거래유형 CHECK, `deal_events`→`deals` 외래키 동작 확인. 시험 행은 롤백, 표는 비어 있음 |
| `0002_auction.sql` | **적용·검증 완료** — `court_jurisdiction`, `auction_stats` 생성, 인덱스 3개, `period_month` CHECK 동작 확인(잘못된 값 거부). 시험 행은 롤백, 표는 비어 있음 |
| `0003_rls.sql` | **적용 완료** — 경매 표 2개 RLS 켬, 정책 없음(anon 접근 불가, 수집기는 postgres 권한으로 우회) |
| `0004_rls_deals.sql` | **적용 완료** — `deals`, `deal_events` RLS 켬 |
| `0005_snapshot_runs.sql` | **적용 완료** — 일일 수집 기록 표(+RLS). bootstrap 판단에 쓴다 |
| `0006_rents.sql` | **적용 완료** — `rents`·`rent_events`(+RLS), `snapshot_runs.kind`(trade/rent) |
| `0007_rent_archive.sql` | **적용 완료** — `rent_monthly`(전월세 요약), `archive_cells`(파일 목록) (+RLS) |

마이그레이션 적용 기록 표(`schema_migrations` 등)는 아직 없다. 새 마이그레이션을 추가하면 이 표를 갱신할 것.
**새 표를 만들면 RLS도 같이 켠다.**

### 다음 할 일

1. ~~`0001` 적용 + RLS~~ 완료 (2026-10-11)
2. ~~매매 일일 수집기~~ 작성·첫 실행 완료 (아래 "일일 수집기")
3. **매일 돌리기**: 기본 브랜치는 `main`이 아니라 **`claude/inspiring-bell-73ixlm`** 이다. 2026-10-11 PR(brave-lamport → inspiring-bell)을 만들었다. 병합되면 Actions 탭에서 `daily-snapshot`을 **수동 실행**(dry_run 먼저)해 러너→공공데이터포털, 러너→Supabase(psql) 접속을 확인. GitHub 시크릿 `DATABASE_URL`이 잘리지 않은 값인지도 이때 확인됨
4. 서울 매매 과거 이력: Actions `backfill` 수동 실행(regions=seoul, months=202001-202508, kinds=trade). 한도 초과로 멈추면 다음 날 재실행
5. ~~전월세 원본 압축 보관 + 요약 표~~ 작성 완료(0007 적용). **Actions 첫 실행에서 릴리스 업로드 확인 필요.** 서울 전월세 과거 이력은 `backfill`을 kinds=rent로 실행
6. 3절 경매 낙찰가율 (NAVER 키 검증 등)

### Actions 실행 확인 (2026-10-12)

- PR jeonghunyang6-code/house-check#1 병합. 기본 브랜치 `claude/inspiring-bell-73ixlm`.
- `daily-snapshot` dry_run: 러너 → 공공데이터포털 정상. 수도권 매매+전월세 64,192건, 실패 0, 13분.
- `daily-snapshot` 실제 실행: 러너 → Supabase(psql) 정상, 전월세 초기 적재·요약(7,130+40,606행) 정상.
  **매매 당월 칸 44개 실패**: 등기일이 전부 NULL 인 칸에서 `UPDATE … FROM (VALUES …)`의 NULL 열이 text 로 추론됨 → `::date` 캐스트로 수정(후속 PR), 재현 테스트 추가. 실패 칸은 트랜잭션이 통째로 취소돼 데이터 손상 없음.
- 아직 미확인: 릴리스 업로드(지난 달 이관이 처음 일어나는 11월 1일 전후, 또는 전월세 backfill 때 확인), 페이지 1000건.

### 2026-10-12 확인 사항

- **서울 매매·전월세 2020-01~2026-08 빠짐없이 적재 완료** (backfill 2회 + 관악구 2칸 수동). 전월세 원본은 Releases `raw-data`에 월별 파일, 요약은 `rent_monthly`.
- **경계 단지 중복**: 국토부는 시군구 경계에 걸친 단지 거래를 두 시군구 응답에 모두 싣는다(예: 관악푸르지오 102동 `11590-3369`, 동작구·관악구). `deal_key` 중복으로 칸 전체가 실패하던 문제를 `load_foreign()`으로 수정(먼저 받은 칸이 가짐). 단지번호 앞 5자리가 지역코드와 다른 거래가 1,610건(497개 단지) 있으나 대부분 중복은 아님.
- **K-apt (공공데이터포털 키로 동작 확인)**
  - 단지 목록: `apis.data.go.kr/1613000/AptListService4/getSigunguAptList4?sigunguCode=11680` (JSON, `kaptCode`·`kaptName`·`bjdCode`·`as1~as3`). 강남구 233개. `getLegaldongAptList4?bjdCode=` 도 됨. `getTotalAptList4`는 연결 실패(미확인)
  - 기본 정보: `AptBasisInfoServiceV5/getAphusBassInfoV5?kaptCode=` → `kaptdaCnt`(세대수)·`hoCnt`·`kaptUsedate`(사용승인일)·`kaptDongCnt`·`kaptTopFloor`·`kaptBcompany`·`codeHeatNm`·`kaptMparea60/85/135/136`(면적대별 세대수). 상세: `getAphusDtlInfoV5` → 주차(`kaptdPcntu`), 지하철(`subwayLine`·`kaptdWtimesub`), 학교 등
  - **K-apt `kaptCode`와 실거래 `aptSeq` 사이 공통 키가 없다.** 법정동(`bjdCode`) + 단지명/지번으로 맞춰야 함(다음 작업)
- **R-ONE (`RONE_API_KEY`, `www.reb.or.kr/r-one/openapi/SttsApiTblData.do?KEY=&Type=json&STATBL_ID=&DTACYCLE_CD=WK&WRTTIME_IDTFR_ID=YYYYWW`)**
  - 표: (주) 매매가격지수 `T244183132827305`, (주) 전세가격지수 `T247713133046872`, (주) 매매수급동향 `T248163133074619`, (주) 전세수급동향 `T245423133086632`. 표 목록 `SttsApiTbl.do`(738개)
  - 기준시점 2026.07.06=100. 지역은 `CLS_FULLNM`(예: `경기>경부2권>수원시>영통구`), 지역 시계열은 `CLS_ID`(서울 50008, 수도권 50002)로 받음(2012년 19주~)
  - **검증**: 2026-10-05 주 서울 +0.12%·수도권 +0.14%·강남 -0.34%·영통 +0.62%, 연속 상승 서울 88주·수도권 84주가 외부 앱 화면과 일치
  - 수도권 83개 중 78개 매칭. 강화·옹진·연천·가평·양평은 주간 조사 대상 아님. 인천 신설 4개 구·화성 4개 구는 1년 전 값 없음. 2025-10-06 주(추석)는 발표 없음
  - 이 환경에서 www.reb.or.kr 연결이 가끔 끊김 → 재시도 필요
- 화면 시안: https://claude.ai/artifact/5vaeqk1AvcDxLhneGS8EL6 (5장: 시장 홈·주간 가격 동향 지도·오늘의 실거래·단지 상세·후보 비교표). 지도 경계는 vuski/admdongkor `ver20260701` 행정동을 시군구로 합침(시군구 코드 83개가 우리 목록과 일치). 시안 생성 스크립트는 아직 저장소에 없음(세션 임시 폴더)
- 사용자 결정 대기: 비교표 관심 단지 목록(네이버 매물·호가와 함께), 웹/모바일 형태(보류, 모바일 폭 카드로 진행 중)

### 저장 방식 (2026-10-11 사용자와 합의)

Supabase 무료(500MB, 제3자 자료 기준·공식 미확인)를 유지한다. 실측: 매매 행당 약 300B, 전월세 약 370B. 서울 월 건수(실측): 매매 1천~1만 6천, 전월세 1만 7천~2만 → 서울 2020~ 전월세 원본만 약 560MB로 한도 초과.

| 데이터 | 저장 위치 |
|---|---|
| 매매 원본 | DB `deals` (서울 2020~ 이력 + 수도권 매일) |
| 전월세 원본 | DB `rents`에는 **당월·전월만**(등록일 추적용). 범위를 벗어난 달은 `jobs/rent_archive.py daily`가 **GitHub Releases `raw-data`의 `rents_YYYYMM.csv.gz`로 옮기고 DB에서 삭제** (등록일 포함) |
| 전월세 과거 이력 | 파일만 (`rent_archive backfill`, DB 원본에 넣지 않음) |
| 전월세 요약 | DB `rent_monthly` (단지×면적군×계약월: 전세·신규 전세 중앙값, 월세 중앙값, 신규·갱신·갱신요구권 건수). D1·D3·D5 재료 |
| 파일 목록 | DB `archive_cells` (어느 시군구·달이 파일에 들어 있는지, 이어받기용) |

- GitHub Releases: 릴리스당 파일 1,000개, 파일당 2GiB 미만, 전체 용량 제한 없음 (docs.github.com "About releases" 2026-10-11 확인). 비공개 저장소라 파일도 비공개. Actions에서 `gh` + `GITHUB_TOKEN`(contents: write)으로 올린다. **이 클라우드 세션에서는 `gh` 인증이 없어 파일 저장소를 쓸 수 없다** → 여기서는 `--archive dir:<경로>`로만 시험.
- 실측(강남 2026-09 전월세 1,119건): CSV.gz 27KB(행당 약 25B, DB의 약 1/15), 요약 450행. 추정: 서울 2020~ 전월세 원본 약 40MB(파일), 요약 약 60만 행(DB 약 90MB, 행 크기 미측정).
- 월별 중앙값끼리는 합칠 수 없다. 여러 달 묶은 시세가 필요하면 배치가 파일을 읽는다.
- 사용자 PC는 주 저장소로 쓰지 않는다(매일 켜져 있어야 함, 웹 대시보드가 못 읽음, 고장 시 등록일 기록 소실). 백업용으로만: 릴리스 화면에서 파일을 내려받으면 된다.

### 일일 수집기 (2026-10-11 작성)

| 파일 | 역할 |
|---|---|
| `collector/regions.py` | 수도권 83개 시군구 코드. **전부 실제 API로 확인**(응답 `sggCd`와 중개사 소재지 이름). 인천 2026-07 개편으로 옛 중구·동구·서구 코드는 0건 → 새 코드(제물포·영종·서해·검단구). 개편 전 계약월도 새 코드로만 조회됨 |
| `collector/snapshot.py` | `diff_snapshot()` 순수 비교 + SQLite 판(테스트용) |
| `collector/db.py` | DB 접근 두 경로: `api`(관리 API, 클라우드 세션) / `psql`(Actions). 값은 `lit()`로만 SQL에 넣는다 |
| `collector/pg_store.py` | Postgres 판 반영(칸마다 트랜잭션 1개), `should_bootstrap()` |
| `jobs/daily.py` | `python -m jobs.daily [--regions seoul] [--months 202001-202512] [--bootstrap] [--db api\|psql] [--dry-run]` |
| `.github/workflows/daily.yml` | 매일 20:47 UTC(05:47 KST), 매매+전월세, 시크릿 `DATA_GO_KR_SERVICE_KEY`·`DATABASE_URL`, psql 경로. **러너에서 미검증** |
| `.github/workflows/backfill.yml` | 과거 이력 수동 적재. 매매는 DB(`--bootstrap --skip-done`), 전월세는 파일+요약(`rent_archive backfill`). 페이지 1000건 시도 |
| `collector/archive.py`, `collector/rent_stats.py`, `jobs/rent_archive.py` | 전월세 파일 보관(CSV.gz, merge)·요약·이관. `tests/test_rent_archive.py`가 로컬 Postgres+로컬 폴더로 전 과정을 검증 |
| `tests/test_pg_store.py` | `HC_TEST_PG_URL`(로컬 빈 Postgres)이 있을 때 SQLite 판과 6단계 시나리오 결과가 같은지 검증 |

- bootstrap 규칙: 처음 받는 (시군구, 계약월) 칸이면서 그 시군구를 최근 3일(오늘 제외) 안에 받은 적이 없으면 `first_seen_date=NULL`. 새 달 칸은 전날 수집이 있었으므로 정상 등록으로 잡힌다.
- 수집이 끊겼다 재개되면 그 사이 등록분의 `first_seen_date`는 재개일로 늦게 찍힌다(`snapshot_runs`의 공백으로 알 수 있음). 4일 이상 끊기면 새 칸은 bootstrap.
- 당월·전월만 본다(설계 4.1). 그보다 늦게 들어오는 해제는 놓친다 → 나중에 주 1회 12개월 재확인을 검토.
- 이 클라우드 환경에서 공공데이터포털 호출은 **자주 끊긴다**(서버가 ~11초 응답이 없으면 프록시 터널 종료). 재시도 5회로 버티며 수도권 전체 1회에 1시간 이상 걸린다. 테스트는 PyPI 차단으로 pytest 대신 최소 실행기(`pytest.raises`만 흉내)로 돌렸다.

## 1. 프로젝트 한 줄 요약

송희구 작가(유튜브 `작가 송희구`, 저서 『나의 첫 번째 부동산 교과서』)의 시세 해석 관점을 데이터로 자동화한
**수도권 아파트 시장 분석기**. **개인용**(나 혼자 사용), 상업·공개 목적 없음.

## 2. 완료된 것

| 영역 | 산출물 | 상태 |
|---|---|---|
| 전체 설계 | `docs/ARCHITECTURE.md` | 완료. 화면, 데이터 모델, 로드맵 8단계 |
| 관점 수집 | `docs/insights/viewpoints.md` | 완료. 유튜브 자막 626개 + 책 전권, 영상 시점·쪽수 출처 |
| 지표 명세 | `docs/insights/indicators.md` | 완료. A~I군 지표의 정의·계산식·기준선·데이터·화면 |
| 출처 정책 | `docs/INSIGHT_SOURCES.md` | 완료. A(본인 채널·저서)·B 등급만 규칙 근거로 사용 |
| 매물·호가 조사 | `docs/LISTING_DATA.md` | 완료. 공식 API 없음. 네이버 소량 수집은 **보류** |
| 경매 낙찰가율 조사 | `docs/AUCTION_DATA.md` | 조사 완료, 구현 일부 (아래 3절) |
| 자막 수집기 | `tools/insight_crawler/` | 완료. `crawl.py`(자막·메타), `triage.py`(주제별 발췌), `vtt.py` |
| 경매 계산 | `analytics/auction.py` + `tests/test_auction.py` | 완료, 테스트 통과 |
| 경매 기사 추출 | `collector/sources/auction_news.py` + `tests/test_auction_news.py` | 완료, **실제 기사로는 미검증** |
| 실거래 수집기(매매) | `collector/sources/molit.py`, `collector/snapshot.py`, `db/migrations/0001_deals.sql`, `tests/test_molit_snapshot.py` | **실제 API로 검증** (강남·송파 2026-09 전량 수집). 일일 수집기·DB 적재는 0절, 전월세 파서는 미작성. `0001`·`0002`는 로컬 Postgres 16에서 적용 검증 완료(2026-10-11), Supabase에 `0001`도 적용 완료(0절) |
| 경매 스키마 | `db/migrations/0002_auction.sql` | **Supabase에 적용·검증 완료** (2026-10-11, 0절). RLS는 `0003_rls.sql` |
| 영상 메타데이터 | `data/sources/youtube/video_metadata_2026-10-11.jsonl` | 영상 672개 요약 (제목·조회수·태그·설명 등) |

테스트: `.venv/bin/pytest -q tests` → 12개 통과 (새 세션에서는 `python -m venv .venv && .venv/bin/pip install -r tools/insight_crawler/requirements.txt pytest`).

## 3. 진행 중: 경매 낙찰가율 (지표 G6)

### 소스 상태

| 소스 | 상태 |
|---|---|
| **지지옥션 월간 경매동향 보도** (NAVER API HUB 뉴스 검색) | **동작 확인 (2026-10-11).** 호출: `GET https://naverapihub.apigw.ntruss.com/search/v1/news`, 헤더 `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY` (기존 `openapi.naver.com`은 401). 검색 요약문(description)만으로 수치가 잡힘. 9월분 확정값: 서울 94.7, **경기 88.8**(경기 겨냥 질의 8종 추가로 기사 5건 일치), 울산 88.5, 대구 82.9. **인천 81.1**(전월 79.1)·전국 85.9도 기사 2건 이상 일치로 확정. 인천은 '낙찰률 문장 → 낙찰가율은 N%로 전달(M%)' 문형이라 추출 패턴 ③을 추가함 |
| 감평협회 「법원경매 용도별/지역별 매각 통계」 | **후보.** 금융 빅데이터 플랫폼이 `abp.bccard.com`으로 이전했고, 이 환경에서는 **403 Access Denied**. 미러 페이지에는 샘플 파일만 확인됨. 월별 컬럼이 있는지 모름 |
| 대법원 법원경매정보 직접 수집 | 제외 (공식 API 없음, 30초 16회 수준에서 1시간 차단) |

### 다음에 할 일 (순서대로)

~~1~4 완료 (2026-10-11): 키 검증, 요약문 수치 확인, 추출기 실제 검색 결과로 검증·보강(정수 임계값 오탐 `80% 아래로` 제거).~~

1. (완료) 환경 변수 설정 여부 확인 (값은 출력하지 않음) — 5절 명령
2. NAVER API HUB **뉴스 검색 API** 1회 호출로 키 검증. 호출 주소·헤더 이름은 API HUB 개발 가이드 기준으로 확인할 것
   (기존 개발자센터는 `openapi.naver.com/v1/search/news.json`, 헤더 `X-Naver-Client-Id`/`X-Naver-Client-Secret`.
   API HUB는 다를 수 있어 **가정하지 말고 가이드 확인**). 키는 절대 출력·로그·커밋하지 않는다
3. `지지옥션 아파트 낙찰가율` 등으로 검색해 **검색 결과 요약문(description)만으로 수치가 잡히는지** 확인.
   기사 본문은 이 환경에서 접근이 막혀 있을 수 있음. 요약에 수치가 없으면 방법 변경 필요 (사용자가 기사를 붙여넣는 방식 등)
4. 추출기(`auction_news.extract`, `confirm`)를 **실제 검색 결과로 검증**하고 정규식 보강
5. 사용자가 감평협회 샘플 파일을 첨부하면: 월 컬럼 유무, 감정 금액 기준(매각 물건 vs 전체), 금액 단위, 최신 기준월 확인 후
   적재기와 `court_jurisdiction` 매핑 작성 (**법원 관할은 기억에 의존하지 말고 파일의 법원명 표기를 보고 작성**)
6. `auction_stats` 적재 → 월별 추이(`rolling_sale_ratio`) → 시장지표 화면용 데이터

## 4. 그다음 단계 (로드맵 순서)

| 순서 | 작업 | 선행 조건 |
|---|---|---|
| A | **1단계 수집기**: 서울 매매·전월세 실거래 일일 스냅샷 + 과거 이력, 등록일(`first_seen_date`) 추적, DB 스키마(`0001`), cron | **공공데이터포털 API 키** (아래 4개 활용 신청). 등록일은 소급 불가이므로 키를 받는 즉시 가장 먼저 시작할 것 |
| B | 단지 분석: K-apt 단지 정보, 전처리(층 보정·직거래 제외), A·B1~B3·C2~C4·D1~D3 지표, 생활권·급지(E0~E4) | A |
| C | 거래량 화면, 가격 동향(R-ONE), 시장지표(ECOS·KOSIS) | 각 API 키 |
| D | 체크리스트 규칙 로더, 🔧 기준선 백테스트(2021 고점·2023 저점), 계산기 | B |
| 보류 | 네이버 부동산 소량 수집 (사용자 PC에서 실행) | 사용자 결정. 설명은 `docs/LISTING_DATA.md` C1 |

**공공데이터포털 활용 신청 4건** (키 1개로 모두 사용): 국토교통부_아파트 매매 실거래가 상세 자료 /
국토교통부_아파트 전월세 실거래가 자료 / 국토교통부_공동주택 기본 정보 / 청약홈 분양정보 조회 서비스.
**사용자가 아직 신청했는지 확인된 바 없음** — 새 세션에서 먼저 물어볼 것.

## 5. 환경과 비밀 값

| 항목 | 내용 |
|---|---|
| NAVER 키 (API HUB) | 환경 변수 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` (사용자가 환경 설정에 등록). **세션 시작 시에만 읽힘.** 설정 여부만 확인: `env \| grep -c '^NAVER'` (값 출력 금지). 0이면 사용자에게 환경 설정 확인 요청 |
| NAVER 서비스 | API HUB에서 **뉴스(NAVER Search News API) 하나만** 신청. 검색어트렌드(Data Lab)는 선택 지표(G7)라 미신청. 결제수단 등록이 요구됨, 한시적 무료, 한도·과금 방식은 콘솔 확인 필요 |
| 허용 도메인 (사용자가 추가함) | `www.data.go.kr`, `bigdata-finance.kr`(→`abp.bccard.com`으로 이전), `abp.bccard.com`, `openapi.naver.com`, `naverapihub.apigw.ntruss.com`, `api.ncloud-docs.com`, `www.youtube.com` 등 |
| 접속 상태 | `www.data.go.kr` 개별 페이지 OK (검색 화면은 연결 끊김). `abp.bccard.com` 403 (**우회 시도 금지**). 네이버 부동산·법원경매정보는 접속 차단 |
| 키 취급 | 채팅에 붙여넣게 하지 말 것. 코드는 환경 변수만 읽고, 로그에 값을 남기지 않는다 |

## 6. 이 저장소에 없는 것 (사용자 PC에 보관 중)

`data/raw/`는 git 제외다. 새 세션에서는 비어 있다. 사용자가 PC에 다음을 보관한다. 필요하면 첨부를 요청한다.

| 파일 | 내용 | 다시 만드는 법 |
|---|---|---|
| `book_notes_2026-10-11.md` (87KB) | 책 전권 읽기 메모 (쪽수 포함). **저작권 때문에 저장소에 올리지 않음** | 책 PDF 7개 재첨부 후 이미지로 재독 (비용 큼) |
| `transcripts_2026-10-11.tar.gz` (2.4MB) | 유튜브 자막 626개 (영상 672개 중, 46개는 자막 없음) | `python -m tools.insight_crawler.crawl` (~1시간, 봇 차단 시 재실행하면 빠진 것만 받음) |
| 책 PDF 7개 | 『나의 첫 번째 부동산 교과서』 | 사용자 PC 원본 |

자막 수집기 재실행 시 `yt-dlp`와 Node.js가 필요하고 `www.youtube.com` 허용이 필요하다 (`js_runtimes: node` 설정 포함).

## 7. 결정 사항 (바꾸려면 사용자와 상의)

1. **개인용.** 로그인·다중 사용자·공개 배포 없음.
2. **예측하지 않는다.** 점수 예측 대신 과열·침체 **관찰 체크리스트** (작가 관점 M1, M2).
3. **실거래가가 종합 점수.** 입지 가중치 합산 점수를 만들지 않는다 (책 p.356).
4. **실거래가·거래량·환금성을 교차 검증**하고, 모든 가격 지표에 거래 건수·신뢰도를 붙인다 (책 p.167).
5. **출처 등급**: 규칙 근거는 A(본인 채널·저서)·B만. 규칙마다 영상 시점 또는 책 쪽수 필수.
6. **차단·접근 제한은 우회하지 않는다.** 네이버 부동산 수집을 하더라도 사용자 PC에서, 소량·저속·로그인 없이, 차단되면 중단, 결과 공유·게시 금지.
7. 책 원문·읽기 메모는 저장소에 올리지 않는다 (저작권). 저장소는 private이지만 공개로 바뀔 수 있음.
8. 작가가 숫자로 말하지 않은 기준선은 🔧로 표시하고 백테스트로 정한다.

## 8. 알려진 한계 (정직하게 기억할 것)

- `auction_news.py`는 기사 전문이 아니라 **검색 요약문(약 100자)** 으로만 검증했다(9월분 약 275건 중 10월 기사 21건에서 후보 추출). 2건 이상 일치 기준 때문에 지역 커버리지가 낮다. 수도권 4개(서울·경기·인천·전국) 9월분은 확정했으나 다른 달은 미검증. 다른 달 기사로는 미검증.
- `0001`·`0002` 마이그레이션은 로컬 Postgres 16(`/usr/lib/postgresql/16/bin`, `su postgres`로 initdb/pg_ctl)에서 적용돼 오류 없음. 이 환경에는 `psql`이 있으나 **PyPI에 접속할 수 없어 psycopg를 설치할 수 없다** 클라우드 세션에서는 Postgres 포트가 막혀 `psql`도 Supabase에 못 붙는다 → **0절의 관리 API**로 접근한다(Actions에서는 pip·직접 접속 가능, 미검증).
- 지표 명세의 🔧 기준선(국면 ±3%·8개월, 하락 지역 70%, 격차 하위 20% 등)은 **초기 추정값**이다.
- 유튜브 자막은 **자동 자막**이라 오인식이 있다. 규칙에 쓰는 핵심 문장은 영상 해당 시점을 확인할 것.
- 관점 카드는 키워드 상위 영상 위주로 읽은 결과다 (영상 약 70개와 입지·재건축 일부 주제는 미정독).
- 전월세 API(`RTMSDataSvcAptRent/getRTMSDataSvcAptRent`) 필드는 2026-10-11 실제 응답으로 확인: `contractType`(신규/갱신), `useRRRight`('사용'=갱신요구권 사용), `preDeposit`·`preMonthlyRent`(종전 보증금·월세), `contractTerm`('26.10~28.10'), `deposit`·`monthlyRent`. 강남 2026-08 200건 중 갱신 89건. **아직 파서는 없다.** 감평협회 파일 구조, 네이버 부동산 응답 필드는 **미확인**이다.
- 매매 API(`RTMSDataSvcAptTradeDev`): `cdealType='O'`=해제, `dealingGbn`=중개거래/직거래, `rgstDate`=등기일(신고일 아님, 소급 불가 문제를 못 푼다). **같은 단지·날짜·면적·층·가격의 별개 거래가 중복**으로 온다(송파 2026-09: 276건 중 키 123개, 직거래 172건) → `keyed()`가 `#순번`을 붙인다. 송파 직거래 172건의 원인은 확인 못 함. `numOfRows=1000`은 이 환경 프록시에서 터널이 끊겨 100건씩 받는다.
- `AptBasisInfoServiceV4` 등 K-apt 서비스 URL은 추측했다가 '서비스 없음' 응답을 받았다. 정확한 서비스명은 포털 활용신청 페이지에서 확인해야 한다. 청약홈(`api.odcloud.kr`)은 허용 도메인에 없어 막힘.
- 이 환경은 다수 외부 사이트에 접속할 수 없어 많은 조사가 웹 검색 결과에 기댔다. 법적 판단은 변호사 자문이 아니다.

## 8-1. 지금 가장 먼저 할 일 (2026-10-11 기준)

경매 낙찰가율(3절)은 **보도 추출로 충분하다고 사용자와 합의하고 보류**했다(감평협회 파일은 `bigdata-finance.kr` 인증서 오류로 못 받음, 우회 금지). 우선순위는 4절 A와 `docs/PRODUCT_PLAN.md`의 트랙 B·C다.

1. ~~DB 접속, 마이그레이션 0001~0006~~ 완료 (0절)
2. ~~시군구 코드·매매/전월세 파서·적재·`jobs/daily.py`·워크플로~~ 작성 완료 (0절 "일일 수집기"). **남은 것: PR 병합 후 Actions 첫 실행 확인 → 서울 매매 과거 이력(backfill) → 전월세 압축 보관·지표 표** (0절 "다음 할 일", "저장 방식")
3. 트랙 C(비주얼 프로토타입)는 DB와 무관해 바로 가능. 사용자 승인 대기 중

## 9. 새 세션 시작 문장

> docs/HANDOFF.md와 docs/PRODUCT_PLAN.md를 읽고 이어서 진행해줘. 0절의 "다음 할 일"부터 해줘 (DB는 Supabase 관리 API로 접속).
> (감평협회 샘플 파일을 받았으면 함께 첨부)

※ `DATA_GO_KR_SERVICE_KEY`는 환경변수로 설정돼 동작 확인됨(2026-10-11). 매매·전월세 API 승인됨. K-apt·청약홈은 미확인. 등록일은 소급 불가이므로 **매일 스냅샷 실행 환경(cron + DB) 결정이 가장 급하다.**

※ (해결됨 — 재등록 후 정상, 길이 112자) 2026-10-11 세션: Supabase용 `DATABASE_URL` 환경변수가 `postgresql://postgres.<프로젝트ID>:` 에서 **끊긴 상태**(43자, 비밀번호·호스트·포트·DB명 없음)로 들어와 있어 접속 불가. 사용자가 다시 등록해야 함. 원인은 확인 못 함(비밀번호의 특수문자가 환경 설정 입력에서 잘렸을 가능성).
