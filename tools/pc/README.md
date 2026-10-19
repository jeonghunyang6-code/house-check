# PC 에서 돌리는 작업

## VWorld 대지면적 (vworld_land.py)

재건축 용적률·대지지분(H5)을 계산하려면 단지 대지면적이 필요한데, 오래된 단지는 건축물대장에 비어 있는 경우가 많다.
VWorld 토지특성 API 로 채우려 했으나 클라우드 서버·GitHub Actions(해외 IP)에서는 접속이 끊겨(2026-10-19) PC 에서 받는다.

- 입력: `vworld_targets.csv` — 2005년 이전 준공 단지의 대표 지번 필지 11,348개 (Claude 가 DB 에서 만든 목록)
- 출력: `vworld_land_result.csv` — 필지별 면적·지목·용도지역·공시지가. 이 파일을 Claude 대화에 첨부하면 DB 에 넣는다
- DB 비밀번호는 필요 없다. VWorld 키만 쓴다(환경 변수, 파일에 저장 안 함)

### 준비 (처음 한 번)
1. Python 설치: https://www.python.org/downloads/ → 설치 화면 첫 페이지에서 **"Add python.exe to PATH" 체크**
2. 이 폴더의 두 파일 `vworld_land.py`, `vworld_targets.csv` 를 PC 의 한 폴더(예: `C:\vworld`)에 받는다

### 실행 (Windows)
1. 시작 메뉴에서 `cmd` (명령 프롬프트) 실행
2. 아래를 한 줄씩 입력 (키 자리에 VWorld 인증키)
   ```
   cd C:\vworld
   set VWORLD_API_KEY=발급받은키
   python vworld_land.py
   ```
3. 1만 1천여 개라 1~2시간 걸린다. 중간에 창을 닫아도 다시 2번을 하면 이어서 받는다
4. 끝나면 같은 폴더의 `vworld_land_result.csv` 를 Claude 대화에 첨부

### 오류가 나면
- `INCORRECT_KEY`(2026-10-19 실제로 나옴, 응답 `{"landCharacteristicss": {"resultCode": "INCORRECT_KEY", ...}}`): 확인할 것
  1. 키를 정확히 넣었는지 — `set VWORLD_API_KEY=키` 에 따옴표·앞뒤 공백 없이
  2. VWorld 인증키 관리 화면의 **서비스 URL** 을 `set VWORLD_DOMAIN=그 URL` 로 넣고 다시 실행 (키가 URL 에 묶여 있다)
  3. 그 키의 활용 API 에 토지특성(국가중점데이터)이 들어 있는지, 키가 승인·사용 중 상태인지
- `HTTP 403/429`·호출 한도: 그날은 멈추고 다음 날 다시 실행
- 처음에 "첫 응답 모양"이 화면에 나온다. 결과가 이상하면 그 줄을 복사해 Claude 에게 보여 준다(키는 안 나온다)
