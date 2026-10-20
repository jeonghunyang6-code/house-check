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

### 부속 필지 (여러 필지에 걸친 단지, 2026-10-20)
대표 필지만으로는 대지면적이 작게 잡혀 용적률이 높게 나오는 단지(목동신시가지5·7·9·11·13 등)가 있다. 건축물대장의 부속 지번 필지 목록이
`vworld_targets_atch.csv`. 같은 폴더에 받아서:
```
python vworld_land.py vworld_targets_atch.csv
```
결과는 같은 `vworld_land_result.csv` 에 이어 붙는다(이미 받은 필지는 건너뜀). 끝나면 그 파일을 다시 첨부.
부속 지번 수집이 며칠 더 이어져 목록이 늘면 새 목록으로 같은 명령을 다시 실행하면 된다.

## 네이버 부동산 '이 화면 호가 저장' 버튼 (2026-10-21)
`naver_ask_bookmarklet.js` 를 북마크 한 줄로 만든 것. 화면에 이미 뜬 매물 글자만 읽어 복사한다(네이버 서버를 따로 부르지 않음, 자동 순회 없음).

1. 크롬 북마크바에서 오른쪽 클릭 → 페이지 추가 → 이름 `호가 저장`, URL 에 아래 한 줄 전체를 붙여넣기
2. 네이버 부동산에서 관심 단지를 열고 왼쪽 매물 목록을 **끝까지 내려** 다 불러온 뒤 `호가 저장` 클릭 → "N건 복사" 알림
3. house-check 상세 탭 → 해당 단지 → `붙여넣기` 칸에 붙여넣고 저장 (처음 한 번은 네이버 단지 번호와 우리 단지를 잇는다)

주 2~3회면 충분하다(호가 추세는 주 단위로 본다). 매물 수 증감을 보려면 매번 목록을 끝까지 불러온 뒤 누른다.
매물을 못 읽으면 '확인용 글자'를 대신 복사하니 그걸 채팅에 붙여넣으면 규칙을 고친다(2026-10-21 첫 사용 0건 → '매매15억' 붙음·'m²' 허용으로 수정).

한 줄 만드는 법: 첫 주석을 빼고 줄을 공백으로 이어 `'javascript:' + encodeURIComponent(코드)`.

```
javascript:(()%20%3D%3E%20%7B%20const%20T%20%3D%20(el)%20%3D%3E%20(el%20%3F%20el.textContent%20%3A%20'').replace(%2F%5Cs%2B%2Fg%2C%20'%20').trim()%3B%20const%20no%20%3D%20(location.pathname.match(%2Fcomplexes%5C%2F(%5Cd%2B)%2F)%20%7C%7C%20%5B%5D)%5B1%5D%20%7C%7C%20null%3B%20const%20PRICE%20%3D%20%2F%5E(%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8%7C%EC%9B%94%EC%84%B8)%5Cs*(%5B0-9%5D%5B0-9%EC%96%B5%2C%5Cs%2F%5D*)%24%2F%3B%20const%20SPEC%20%3D%20%2F(%E3%8E%A1%7Cm%C2%B2%7Cm2)%2F%3B%20let%20items%20%3D%20%5B%5D%3B%20const%20cards%20%3D%20%5B...document.querySelectorAll('.item')%5D.filter(el%20%3D%3E%20el.querySelector('.price_line'))%3B%20for%20(const%20el%20of%20cards)%20%7B%20const%20ty%20%3D%20T(el.querySelector('.price_line%20.type'))%2C%20pr%20%3D%20T(el.querySelector('.price_line%20.price'))%3B%20const%20p%20%3D%20(ty%20%2B%20'%20'%20%2B%20pr).match(PRICE)%3B%20if%20(!p)%20continue%3B%20const%20spec%20%3D%20%5B...el.querySelectorAll('.info_area%20.spec%2C%20.spec')%5D.map(T).find(s%20%3D%3E%20SPEC.test(s)%20%26%26%20%2F%EC%B8%B5%2F.test(s))%20%7C%7C%20''%3B%20const%20c%20%3D%20T(el).match(%2F%ED%99%95%EC%9D%B8%EB%A7%A4%EB%AC%BC%5Cs*(%5Cd%7B2%7D%5C.%5Cd%7B2%7D%5C.%5Cd%7B2%7D)%2F)%2C%20d%20%3D%20T(el.querySelector('.item_title')).match(%2F(%5Cd%2B)%EB%8F%99%2F)%3B%20items.push(%7B%20type%3A%20p%5B1%5D%2C%20price%3A%20p%5B2%5D.trim()%2C%20spec%2C%20conf%3A%20c%20%3F%20c%5B1%5D%20%3A%20''%2C%20dong%3A%20d%20%3F%20d%5B1%5D%20%3A%20''%20%7D)%3B%20%7D%20const%20L%20%3D%20document.body.innerText.split('%5Cn').map(s%20%3D%3E%20s.trim()).filter(Boolean)%3B%20if%20(!items.length)%20%7B%20for%20(let%20i%20%3D%200%3B%20i%20%3C%20L.length%3B%20i%2B%2B)%20%7B%20const%20p%20%3D%20L%5Bi%5D.match(PRICE)%3B%20if%20(!p)%20continue%3B%20let%20spec%20%3D%20''%2C%20conf%20%3D%20''%2C%20dong%20%3D%20''%3B%20for%20(let%20k%20%3D%20Math.max(0%2C%20i%20-%203)%3B%20k%20%3C%20Math.min(L.length%2C%20i%20%2B%208)%3B%20k%2B%2B)%20%7B%20if%20(k%20%3E%20i%20%26%26%20PRICE.test(L%5Bk%5D))%20break%3B%20if%20(k%20%3C%20i)%20%7B%20const%20d%20%3D%20L%5Bk%5D.match(%2F(%5Cd%2B)%EB%8F%99%24%2F)%3B%20if%20(d)%20dong%20%3D%20d%5B1%5D%3B%20%7D%20if%20(k%20%3E%20i%20%26%26%20!spec%20%26%26%20SPEC.test(L%5Bk%5D)%20%26%26%20%2F%EC%B8%B5%2F.test(L%5Bk%5D))%20spec%20%3D%20L%5Bk%5D%3B%20if%20(k%20%3E%20i%20%26%26%20!conf)%20%7B%20const%20c%20%3D%20L%5Bk%5D.match(%2F%ED%99%95%EC%9D%B8%EB%A7%A4%EB%AC%BC%5Cs*(%5Cd%7B2%7D%5C.%5Cd%7B2%7D%5C.%5Cd%7B2%7D)%2F)%3B%20if%20(c)%20conf%20%3D%20c%5B1%5D%3B%20%7D%20%7D%20items.push(%7B%20type%3A%20p%5B1%5D%2C%20price%3A%20p%5B2%5D.trim()%2C%20spec%2C%20conf%2C%20dong%20%7D)%3B%20%7D%20%7D%20let%20s%2C%20msg%3B%20if%20(items.length)%20%7B%20s%20%3D%20JSON.stringify(%7B%20src%3A%20'naver'%2C%20no%2C%20at%3A%20new%20Date(Date.now()%20-%20new%20Date().getTimezoneOffset()%20*%2060000).toISOString().slice(0%2C%2010)%2C%20n%3A%20items.length%2C%20items%20%7D)%3B%20msg%20%3D%20%60%ED%98%B8%EA%B0%80%20%24%7Bitems.length%7D%EA%B1%B4%EC%9D%84%20%EB%B3%B5%EC%82%AC%ED%96%88%EC%8A%B5%EB%8B%88%EB%8B%A4.%20house-check%20%EC%83%81%EC%84%B8%20%ED%83%AD%20'%EB%B6%99%EC%97%AC%EB%84%A3%EA%B8%B0'%EC%97%90%20%EB%84%A3%EC%96%B4%20%EC%A3%BC%EC%84%B8%EC%9A%94.%60%3B%20%7D%20else%20%7B%20const%20i0%20%3D%20Math.max(0%2C%20L.findIndex(x%20%3D%3E%20%2F%ED%99%95%EC%9D%B8%EB%A7%A4%EB%AC%BC%2F.test(x))%20-%2012)%2C%20first%20%3D%20cards%5B0%5D%20%7C%7C%20document.querySelector('.item')%3B%20s%20%3D%20'%5Bhouse-check%20%ED%99%95%EC%9D%B8%EC%9A%A9%5D%5Cn'%20%2B%20location.pathname%20%2B%20'%5Cn'%20%2B%20L.slice(i0%2C%20i0%20%2B%2040).join('%5Cn')%20%2B%20'%5Cn---%5Cn'%20%2B%20(first%20%3F%20first.outerHTML.replace(%2F%3Cimg%5B%5E%3E%5D*%3E%2Fg%2C%20'').slice(0%2C%202500)%20%3A%20'(item%20%EC%97%86%EC%9D%8C)')%3B%20msg%20%3D%20'%EB%A7%A4%EB%AC%BC%EC%9D%84%20%EC%9D%BD%EC%A7%80%20%EB%AA%BB%ED%95%B4%20%ED%99%95%EC%9D%B8%EC%9A%A9%20%EA%B8%80%EC%9E%90%EB%A5%BC%20%EB%8C%80%EC%8B%A0%20%EB%B3%B5%EC%82%AC%ED%96%88%EC%8A%B5%EB%8B%88%EB%8B%A4.%20Claude%20%EC%B1%84%ED%8C%85%EC%97%90%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%96%B4%20%EC%A3%BC%EC%84%B8%EC%9A%94.'%3B%20%7D%20const%20done%20%3D%20()%20%3D%3E%20alert(msg)%3B%20if%20(navigator.clipboard)%20navigator.clipboard.writeText(s).then(done%2C%20()%20%3D%3E%20prompt('%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%9C%BC%EC%84%B8%EC%9A%94'%2C%20s))%3B%20else%20prompt('%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%9C%BC%EC%84%B8%EC%9A%94'%2C%20s)%3B%20%7D)()%3B
```
