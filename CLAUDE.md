# house-check

개인용 수도권 아파트 시장 분석기. **작업을 시작하기 전에 `docs/HANDOFF.md`를 읽는다.** (현재 상태, 다음 할 일, 결정 사항, 알려진 한계)

## 문서 지도

| 문서 | 내용 |
|---|---|
| `docs/HANDOFF.md` | 진행 현황·다음 작업·환경 (가장 먼저) |
| `docs/ARCHITECTURE.md` | 전체 설계, 화면, 데이터 모델, 로드맵 |
| `docs/insights/viewpoints.md` | 송희구 관점 카드 (영상 시점·책 쪽수 출처) |
| `docs/insights/indicators.md` | 지표 구현 명세 (정의·계산식·기준선·데이터) |
| `docs/LISTING_DATA.md`, `docs/AUCTION_DATA.md` | 매물·호가, 경매 낙찰가율 데이터 확보 방안 |
| `docs/INSIGHT_SOURCES.md` | 출처 등급 정책 |

## 규칙

- **비밀 값**: API 키는 환경 변수로만 읽는다 (`NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 등). 출력·로그·커밋 금지. 사용자가 채팅에 키를 붙여넣으려 하면 막고 환경 설정을 안내한다.
- **원자료 커밋 금지**: `data/raw/`는 git 제외. 책 원문·읽기 메모(저작권)는 저장소에 올리지 않는다.
- **접근 제한 우회 금지**: 403·429·캡차가 나오면 멈춘다. 브라우저 위장, IP 변경 등은 하지 않는다.
- **지표 기준선**: 작가가 숫자로 말한 것은 그대로, 아닌 것은 🔧로 표시하고 백테스트로 정한다. 출처(영상 시점 또는 책 쪽수) 없는 규칙은 만들지 않는다.
- **정직한 보고**: 검증하지 못한 것(실제 데이터로 못 돌려본 코드, 확인 못 한 필드명)은 그렇다고 말한다.
- 사용자는 한국어로 대화한다. 문서는 한국어, 코드 식별자는 영어.

## 개발

```
python -m venv .venv && .venv/bin/pip install -r tools/insight_crawler/requirements.txt pytest sqlglot
.venv/bin/pytest -q tests
```

브랜치: `claude/inspiring-bell-73ixlm`. 푸시는 이 브랜치로만.
