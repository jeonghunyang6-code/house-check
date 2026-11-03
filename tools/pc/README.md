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

## 네이버 부동산 '이 화면 호가 저장' 버튼 (2026-10-21, 2026-11-03 새 화면 fin.land.naver.com 대응)
`naver_ask_bookmarklet.js` 를 북마크 한 줄로 만든 것. 화면에 이미 뜬 매물 글자만 읽는다(네이버 서버를 따로 부르지 않음, 자동 순회 없음).

1. 크롬 북마크바의 기존 `호가 저장` 북마크를 오른쪽 클릭 → 수정 → URL 칸을 아래 한 줄 전체로 **바꿔** 저장(새로 만들 때는 페이지 추가)
2. 네이버 부동산에서 관심 단지를 열고 매물 목록을 **끝까지 내려** 다 불러온 뒤 `호가 저장` 클릭 → house-check 가 새 탭으로 열리며 바로 저장(팝업이 막히면 "N건 복사" → 상세 탭 '붙여넣기')
3. 처음 보는 단지는 이름으로 찾아 잇고, 못 찾으면 상세 탭 위에 '어느 단지인가요?' 상자가 뜬다(한 번 고르면 기억)

새 화면(2026-11-03): 칸 이름을 몰라 화면 글자 줄로 읽는다. '매매 15억 5,000'·'매매' 다음 줄 '15억' 모두 가격, 그 아래에서 전용면적·층·향·동·확인일.
- 절반 넘는 매물의 면적을 못 읽으면 저장하지 않고 '면적 확인용' 글자를 복사한다(2026-11-03 새 화면에서 면적을 1·2·3 으로 잘못 읽어 저장된 일) → 채팅에 붙여넣기
- 매물을 못 읽으면 '확인용 글자'(주소·제목·가격 주변 글자·첫 매물 칸)를 복사한다 → 채팅에 붙여넣으면 규칙을 고친다
- 오류가 나면 'house-check 호가 저장 오류: …' 창이 뜬다 → 그 문구를 채팅에
- **아무 반응이 없으면** 그 사이트가 북마크 실행을 막는 것 → 매물 목록을 띄운 채 Ctrl+A, Ctrl+C 하고 house-check 상세 탭 '붙여넣기'에 넣는다(같은 규칙으로 읽음)

주 2~3회면 충분하다(호가 추세는 주 단위로 본다). 매물 수 증감을 보려면 매번 목록을 끝까지 불러온 뒤 누른다.

한 줄 만드는 법: 첫 주석을 빼고 줄을 공백으로 이어 `'javascript:' + encodeURIComponent(코드)`.

```
javascript:(()%20%3D%3E%20%7B%20try%20%7B%20const%20L%20%3D%20document.body.innerText.split('%5Cn').map(s%20%3D%3E%20s.replace(%2F%5Cs%2B%2Fg%2C%20'%20').trim()).filter(Boolean)%3B%20const%20TY%20%3D%20%2F%5E(%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8%7C%EC%9B%94%EC%84%B8)%24%2F%2C%20PR%20%3D%20%2F%5E(%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8%7C%EC%9B%94%EC%84%B8)%5Cs*(%5B0-9%5D%5B0-9%EC%96%B5%EB%A7%8C%2C%5Cs%2F%5D*)%24%2F%2C%20NUM%20%3D%20%2F%5E%5B0-9%5D%5B0-9%EC%96%B5%EB%A7%8C%2C%5Cs%2F%5D*%24%2F%3B%20const%20q%20%3D%20new%20URLSearchParams(location.search)%2C%20href%20%3D%20location.pathname%20%2B%20location.search%3B%20const%20no%20%3D%20(location.pathname.match(%2Fcomplexes%5C%2F(%5Cd%2B)%2F)%20%7C%7C%20%5B%5D)%5B1%5D%20%7C%7C%20q.get('complexNumber')%20%7C%7C%20q.get('complexNo')%20%7C%7C%20q.get('complex')%20%7C%7C%20(href.match(%2Fcomplex(%3F%3Aes%7CNo%7CNumber)%3F%5B%3D%2F%5D(%5Cd%2B)%2Fi)%20%7C%7C%20%5B%5D)%5B1%5D%20%7C%7C%20null%3B%20const%20area%20%3D%20(w)%20%3D%3E%20%7B%20const%20e%20%3D%20w.match(%2F%EC%A0%84%EC%9A%A9%5Cs*(%3F%3A%EB%A9%B4%EC%A0%81)%3F%5Cs*(%5Cd%2B(%3F%3A%5C.%5Cd%2B)%3F)%5Cs*(%3F%3A%E3%8E%A1%7Cm%C2%B2%7Cm2)%2F)%3B%20if%20(e)%20return%20%2Be%5B1%5D%3B%20const%20p%20%3D%20w.match(%2F(%5Cd%2B(%3F%3A%5C.%5Cd%2B)%3F)%5BA-Z%5D*%5Cs*%5C%2F%5Cs*(%5Cd%2B(%3F%3A%5C.%5Cd%2B)%3F)%5Cs*(%3F%3A%E3%8E%A1%7Cm%C2%B2%7Cm2)%2F)%3B%20if%20(p)%20return%20Math.min(%2Bp%5B1%5D%2C%20%2Bp%5B2%5D)%3B%20const%20o%20%3D%20w.match(%2F(%5Cd%2B(%3F%3A%5C.%5Cd%2B)%3F)%5Cs*(%3F%3A%E3%8E%A1%7Cm%C2%B2%7Cm2)%2F)%3B%20if%20(o)%20return%20%2Bo%5B1%5D%3B%20const%20t%20%3D%20w.match(%2F(%3F%3A%5E%7C%5B%5Cs%7C%C2%B7%2C%5D)(%5Cd%7B2%2C3%7D)%5BA-Z%5D%7B1%2C2%7D(%3F%3D%24%7C%5B%5Cs%7C%C2%B7%2C%5D)%2F)%3B%20return%20t%20%3F%20%2Bt%5B1%5D%20%3A%20null%3B%20%7D%3B%20%20%20%2F*%20%EC%A3%BC%ED%83%9D%ED%98%95%20'84A'(%E3%8E%A1%20%EC%97%86%EC%9D%B4)%20%3D%20%EC%A0%84%EC%9A%A9%EB%A9%B4%EC%A0%81%20%EC%A0%95%EC%88%98%20*%2F%20const%20items%20%3D%20%5B%5D%3B%20for%20(let%20i%20%3D%200%3B%20i%20%3C%20L.length%3B%20i%2B%2B)%20%7B%20let%20ty%2C%20pr%2C%20j%20%3D%20i%3B%20const%20a%20%3D%20L%5Bi%5D.match(PR)%3B%20if%20(a)%20%7B%20ty%20%3D%20a%5B1%5D%3B%20pr%20%3D%20a%5B2%5D%3B%20%7D%20else%20if%20(TY.test(L%5Bi%5D)%20%26%26%20i%20%2B%201%20%3C%20L.length%20%26%26%20NUM.test(L%5Bi%20%2B%201%5D))%20%7B%20ty%20%3D%20L%5Bi%5D%3B%20pr%20%3D%20L%5Bi%20%2B%201%5D%3B%20j%20%3D%20i%20%2B%201%3B%20%7D%20else%20continue%3B%20if%20(ty%20!%3D%3D%20'%EC%9B%94%EC%84%B8'%20%26%26%20!%2F%EC%96%B5%2F.test(pr)%20%26%26%20%2Bpr.replace(%2F%5B%5E0-9%5D%2Fg%2C%20'')%20%3C%201000)%20continue%3B%20%20%20%2F*%20'%EB%A7%A4%EB%A7%A4%2036'%20%3D%20%EB%A7%A4%EB%AC%BC%20%EA%B0%9C%EC%88%98%20%ED%83%AD%20*%2F%20let%20k%20%3D%20j%20%2B%201%3B%20while%20(k%20%3C%20L.length%20%26%26%20k%20%3C%20j%20%2B%2012%20%26%26%20!PR.test(L%5Bk%5D)%20%26%26%20!(TY.test(L%5Bk%5D)%20%26%26%20NUM.test(L%5Bk%20%2B%201%5D%20%7C%7C%20'')))%20k%2B%2B%3B%20const%20w%20%3D%20L.slice(j%20%2B%201%2C%20k).join('%20%7C%20')%2C%20before%20%3D%20L.slice(Math.max(0%2C%20i%20-%203)%2C%20i).join('%20%7C%20')%3B%20const%20fl%20%3D%20w.match(%2F(%5B0-9%EC%A0%80%EC%A4%91%EA%B3%A0%5D%2B)%5Cs*%5C%2F%5Cs*(%5Cd%2B)%5Cs*%EC%B8%B5%2F)%2C%20dir%20%3D%20w.match(%2F(%5B%EB%8F%99%EC%84%9C%EB%82%A8%EB%B6%81%5D%7B1%2C2%7D)%ED%96%A5%2F)%2C%20d%20%3D%20(before%20%2B%20'%20%7C%20'%20%2B%20w).match(%2F(%5Cd%2B)%5Cs*%EB%8F%99(%3F!%5B%EA%B0%80-%ED%9E%A3%5D)%2F)%3B%20const%20c%20%3D%20w.match(%2F%ED%99%95%EC%9D%B8(%3F%3A%EB%A7%A4%EB%AC%BC)%3F%5Cs*(%5Cd%7B2%7D%5C.%5Cd%7B2%7D%5C.%5Cd%7B2%7D)%2F)%20%7C%7C%20w.match(%2F(%5Cd%7B2%7D%5C.%5Cd%7B2%7D%5C.%5Cd%7B2%7D)%5C.%3F%5Cs*%ED%99%95%EC%9D%B8%2F)%3B%20const%20ex0%20%3D%20area(w)%2C%20ex%20%3D%20ex0%20%26%26%20ex0%20%3E%3D%2015%20%3F%20ex0%20%3A%20null%3B%20items.push(%7B%20type%3A%20ty%2C%20price%3A%20pr.trim()%2C%20ex%2C%20fl%3A%20fl%20%3F%20fl%5B1%5D%20%3A%20''%2C%20tot%3A%20fl%20%3F%20%2Bfl%5B2%5D%20%3A%200%2C%20dir%3A%20dir%20%3F%20dir%5B1%5D%20%2B%20'%ED%96%A5'%20%3A%20''%2C%20spec%3A%20w.slice(0%2C%20120)%2C%20conf%3A%20c%20%3F%20c%5B1%5D%20%3A%20''%2C%20dong%3A%20d%20%3F%20d%5B1%5D%20%3A%20''%20%7D)%3B%20i%20%3D%20k%20-%201%3B%20%7D%20%2F*%20%EB%8B%A8%EC%A7%80%20%EC%9D%B4%EB%A6%84%3A%20%EC%98%9B%20%ED%99%94%EB%A9%B4%20'%EC%95%84%ED%8C%8C%ED%8A%B8%20%2F%201541%EC%84%B8%EB%8C%80'%20%EC%9C%84%20%EC%A4%84%2C%20%EC%83%88%20%ED%99%94%EB%A9%B4%EC%9D%80%20'%EC%84%B8%EB%8C%80'%20%EA%B0%80%20%EB%93%A0%20%EC%A4%84%20%EC%9C%84%20%EB%98%90%EB%8A%94%20%EB%AC%B8%EC%84%9C%20%EC%A0%9C%EB%AA%A9%20%EC%95%9E%EB%B6%80%EB%B6%84%20*%2F%20const%20hi%20%3D%20L.findIndex(x%20%3D%3E%20%2F%5E%EC%95%84%ED%8C%8C%ED%8A%B8%5Cs*%5C%2F%5Cs*%5B%5Cd%2C%5D%2B%EC%84%B8%EB%8C%80%2F.test(x)%20%7C%7C%20%2F%5E%5B%5Cd%2C%5D%2B%EC%84%B8%EB%8C%80%2F.test(x))%3B%20const%20nm%20%3D%20(hi%20%3E%200%20%3F%20L%5Bhi%20-%201%5D%20%3A%20document.title.split(%2F%5Cs%5B-%7C%3A%5D%5Cs%2F)%5B0%5D).replace(%2F%5B%E2%98%85%E2%98%86%5D%2Fg%2C%20'').trim()%3B%20let%20s%2C%20msg%3B%20%2F*%202026-11-03%3A%20%EC%83%88%20%ED%99%94%EB%A9%B4%EC%97%90%EC%84%9C%20%EB%A9%B4%EC%A0%81%EC%9D%84%201%C2%B72%C2%B73%20%EC%9C%BC%EB%A1%9C%20%EC%9E%98%EB%AA%BB%20%EC%9D%BD%EC%96%B4%20%EC%A0%80%EC%9E%A5%EB%90%A8%20%E2%86%92%20%EC%A0%88%EB%B0%98%20%EB%84%98%EA%B2%8C%20%EB%A9%B4%EC%A0%81%EC%9D%84%20%EB%AA%BB%20%EC%9D%BD%EC%9C%BC%EB%A9%B4%20%EC%A0%80%EC%9E%A5%ED%95%98%EC%A7%80%20%EC%95%8A%EA%B3%A0%20%ED%99%95%EC%9D%B8%EC%9A%A9(%EB%A7%A4%EB%AC%BC%20%EC%A3%BC%EB%B3%80%20%EA%B8%80%EC%9E%90)%EC%9D%84%20%EB%B3%B5%EC%82%AC%20*%2F%20const%20miss%20%3D%20items.filter(x%20%3D%3E%20!x.ex).length%3B%20if%20(items.length%20%26%26%20miss%20*%202%20%3E%20items.length)%20%7B%20s%20%3D%20'%5Bhouse-check%20%EB%A9%B4%EC%A0%81%20%ED%99%95%EC%9D%B8%EC%9A%A9%5D%5Cn'%20%2B%20href%20%2B%20'%5Cn'%20%2B%20document.title%20%2B%20'%5Cn'%20%2B%20items.slice(0%2C%208).map(x%20%3D%3E%20%60%24%7Bx.type%7D%20%24%7Bx.price%7D%20%E2%87%92%20%24%7Bx.spec%7D%60).join('%5Cn')%20%2B%20'%5Cn---%5Cn'%20%2B%20L.slice(0%2C%20120).join('%5Cn')%3B%20msg%20%3D%20%60%EB%A7%A4%EB%AC%BC%20%24%7Bitems.length%7D%EA%B1%B4%20%EC%A4%91%20%24%7Bmiss%7D%EA%B1%B4%EC%9D%98%20%EB%A9%B4%EC%A0%81%EC%9D%84%20%EB%AA%BB%20%EC%9D%BD%EC%96%B4%20%EC%A0%80%EC%9E%A5%ED%95%98%EC%A7%80%20%EC%95%8A%EC%95%98%EC%8A%B5%EB%8B%88%EB%8B%A4.%20%ED%99%95%EC%9D%B8%EC%9A%A9%20%EA%B8%80%EC%9E%90%EB%A5%BC%20%EB%B3%B5%EC%82%AC%ED%96%88%EC%9C%BC%EB%8B%88%20Claude%20%EC%B1%84%ED%8C%85%EC%97%90%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%96%B4%20%EC%A3%BC%EC%84%B8%EC%9A%94.%60%3B%20%7D%20else%20if%20(items.length)%20%7B%20s%20%3D%20JSON.stringify(%7B%20src%3A%20'naver'%2C%20v%3A%202%2C%20no%2C%20nm%2C%20at%3A%20new%20Date(Date.now()%20-%20new%20Date().getTimezoneOffset()%20*%2060000).toISOString().slice(0%2C%2010)%2C%20n%3A%20items.length%2C%20items%20%7D)%3B%20%2F*%20%EC%A3%BC%EC%86%8C%20%23%20%EB%92%A4%EB%8A%94%20%EC%84%9C%EB%B2%84%EB%A1%9C%20%EC%95%88%20%EA%B0%90.%20%ED%8C%9D%EC%97%85%EC%9D%B4%20%EB%A7%89%ED%9E%88%EB%A9%B4%20%EB%B3%B5%EC%82%AC.%20%ED%95%9C%20%EC%A4%84%20%EB%B6%81%EB%A7%88%ED%81%AC%EB%9D%BC%20%2F%2F%20%EC%A3%BC%EC%84%9D%20%EA%B8%88%EC%A7%80%20*%2F%20const%20w%20%3D%20window.open('https%3A%2F%2Fhouse-check-brown.vercel.app%2F%23ask%3D'%20%2B%20encodeURIComponent(s)%2C%20'house-check')%3B%20if%20(w)%20return%3B%20msg%20%3D%20%60%ED%98%B8%EA%B0%80%20%24%7Bitems.length%7D%EA%B1%B4%EC%9D%84%20%EB%B3%B5%EC%82%AC%ED%96%88%EC%8A%B5%EB%8B%88%EB%8B%A4.%20house-check%20%EC%83%81%EC%84%B8%20%ED%83%AD%20'%EB%B6%99%EC%97%AC%EB%84%A3%EA%B8%B0'%EC%97%90%20%EB%84%A3%EC%96%B4%20%EC%A3%BC%EC%84%B8%EC%9A%94.%60%3B%20%7D%20else%20%7B%20const%20i0%20%3D%20Math.max(0%2C%20L.findIndex(x%20%3D%3E%20%2F%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8%2F.test(x)%20%26%26%20%2F%5B0-9%5D%2F.test(x))%20-%208)%3B%20const%20tw%20%3D%20document.createTreeWalker(document.body%2C%20NodeFilter.SHOW_TEXT)%3B%20let%20n%2C%20card%20%3D%20null%3B%20while%20((n%20%3D%20tw.nextNode()))%20%7B%20if%20(%2F%5E%5Cs*(%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8)%5Cs*%5B0-9%5D%2F.test(n.nodeValue)%20%7C%7C%20%2F%5E%5Cs*(%EB%A7%A4%EB%A7%A4%7C%EC%A0%84%EC%84%B8)%5Cs*%24%2F.test(n.nodeValue))%20%7B%20card%20%3D%20n.parentElement%3B%20break%3B%20%7D%20%7D%20for%20(let%20u%20%3D%200%3B%20card%20%26%26%20u%20%3C%206%20%26%26%20card.parentElement%20%26%26%20card.innerText.length%20%3C%20120%3B%20u%2B%2B)%20card%20%3D%20card.parentElement%3B%20s%20%3D%20'%5Bhouse-check%20%ED%99%95%EC%9D%B8%EC%9A%A9%20v2%5D%5Cn'%20%2B%20href%20%2B%20'%5Cn'%20%2B%20document.title%20%2B%20'%5Cn'%20%2B%20L.slice(i0%2C%20i0%20%2B%2050).join('%5Cn')%20%2B%20'%5Cn---%5Cn'%20%2B%20(card%20%3F%20card.outerHTML.replace(%2F%3C(img%7Csvg%7Cpath)%5B%5E%3E%5D*%3E%2Fg%2C%20'').replace(%2F%5Cs(style%7Cd)%3D%22%5B%5E%22%5D*%22%2Fg%2C%20'').slice(0%2C%203000)%20%3A%20'(%EB%A7%A4%EB%AC%BC%20%EC%B9%B8%20%EC%97%86%EC%9D%8C)')%3B%20msg%20%3D%20'%EB%A7%A4%EB%AC%BC%EC%9D%84%20%EC%9D%BD%EC%A7%80%20%EB%AA%BB%ED%95%B4%20%ED%99%95%EC%9D%B8%EC%9A%A9%20%EA%B8%80%EC%9E%90%EB%A5%BC%20%EB%8C%80%EC%8B%A0%20%EB%B3%B5%EC%82%AC%ED%96%88%EC%8A%B5%EB%8B%88%EB%8B%A4.%20Claude%20%EC%B1%84%ED%8C%85%EC%97%90%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%96%B4%20%EC%A3%BC%EC%84%B8%EC%9A%94.'%3B%20%7D%20const%20done%20%3D%20()%20%3D%3E%20alert(msg)%3B%20if%20(navigator.clipboard)%20navigator.clipboard.writeText(s).then(done%2C%20()%20%3D%3E%20prompt('%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%9C%BC%EC%84%B8%EC%9A%94'%2C%20s))%3B%20else%20prompt('%EB%B3%B5%EC%82%AC%ED%95%B4%EC%84%9C%20%EB%B6%99%EC%97%AC%EB%84%A3%EC%9C%BC%EC%84%B8%EC%9A%94'%2C%20s)%3B%20%7D%20catch%20(e)%20%7B%20alert('house-check%20%ED%98%B8%EA%B0%80%20%EC%A0%80%EC%9E%A5%20%EC%98%A4%EB%A5%98%3A%20'%20%2B%20e.message)%3B%20%7D%20%7D)()%3B
```
