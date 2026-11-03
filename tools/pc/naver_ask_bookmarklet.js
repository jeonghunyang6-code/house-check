/* 네이버 부동산 '이 화면 호가 저장' 북마크 버튼 (2026-10-21 사용자 결정, 2026-11-03 새 화면 fin.land.naver.com 대응).
   쓰는 법: 네이버 부동산에서 단지를 열고 매물 목록을 끝까지 내려 다 불러온 뒤 북마크를 누른다.
   → 화면에 보이는 매물(거래 방식·가격·전용면적·층·향·동·확인일)을 읽어 house-check 사이트를 새 탭으로 열며 바로 저장.
     팝업이 막히면 클립보드에 복사 → 상세 탭 '붙여넣기'.
   하는 일: 이미 화면에 뜬 글자만 읽는다. 네이버 서버를 따로 부르지 않고, 다른 페이지를 돌지 않는다(자동 수집·위장 없음).
   읽는 법(2026-11-03): 새 화면의 칸 이름(class)을 몰라 화면 글자 줄로만 읽는다. '매매 15억 5,000'·'매매15억'·'매매' 다음 줄 '15억'
     모두 가격으로 보고, 다음 가격 줄 전까지에서 전용면적(㎡·m²: '전용' 붙은 값 > '공급/전용' 의 뒤 값 > 하나뿐인 값)·층(12/25층, 저/15층)·향·동·확인일을 찾는다.
   0건이면 확인용(주소·제목·가격 주변 글자·첫 매물 칸 HTML)을 복사한다 → 채팅에 붙여넣어 규칙을 고친다. 오류가 나면 오류 문구를 알린다.
   아무 반응이 없으면 그 사이트가 북마크 실행 자체를 막는 것 → 매물 목록에서 Ctrl+A, Ctrl+C 후 house-check 상세 탭 '붙여넣기'(같은 규칙으로 읽음).
   북마크 주소로 쓰는 한 줄은 tools/pc/README.md (만드는 법도 거기) */
(() => { try {
  const L = document.body.innerText.split('\n').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  const TY = /^(매매|전세|월세)$/, PR = /^(매매|전세|월세)\s*([0-9][0-9억만,\s/]*?)\s*(?:~.*)?$/, NUM = /^[0-9][0-9억만,\s/]*(?:~.*)?$/;
  const q = new URLSearchParams(location.search), href = location.pathname + location.search;
  const no = (location.pathname.match(/complexes\/(\d+)/) || [])[1] || q.get('complexNumber') || q.get('complexNo') || q.get('complex')
    || (href.match(/complex(?:es|No|Number)?[=/](\d+)/i) || [])[1] || null;
  /* 전용면적: 새 화면 '아파트116B1㎡ (전용84.62B1)'(2026-11-03, 'B1㎡' 의 1 을 면적으로 읽던 것) > '공급/전용㎡' 작은 값 > 'N㎡' > 주택형 '84A'. '평' 단위 화면이면 ㎡ 로 */
  const area = (w) => { let v = null; const e = w.match(/전용\s*(?:면적)?\s*(\d+(?:\.\d+)?)/); if (e) v = +e[1];
    if (v == null) { const p = w.match(/(\d+(?:\.\d+)?)[A-Z0-9]*\s*\/\s*(\d+(?:\.\d+)?)[A-Z0-9]*\s*(?:㎡|m²|m2)/); if (p) v = Math.min(+p[1], +p[2]); }
    if (v == null) { const o = w.match(/(?:^|[^0-9A-Z.])(\d+(?:\.\d+)?)\s*(?:㎡|m²|m2)/); if (o) v = +o[1]; }
    if (v == null) { const t = w.match(/(?:^|[\s|·,])(\d{2,3})[A-Z]{1,2}(?=$|[\s|·,])/); if (t) v = +t[1]; }
    return v != null && /평/.test(w) && !/㎡|m²|m2/.test(w) ? Math.round(v * 330.58) / 100 : v; };
  const items = [];
  for (let i = 0; i < L.length; i++) {
    let ty, pr, j = i;
    const a = L[i].match(PR);
    if (a) { ty = a[1]; pr = a[2]; } else if (TY.test(L[i]) && i + 1 < L.length && NUM.test(L[i + 1])) { ty = L[i]; pr = L[i + 1]; j = i + 1; } else continue;
    if (!/억|\//.test(pr) && +pr.replace(/[^0-9]/g, '') < 1000) continue;   /* '매매 36'·'월세 6' = 매물 개수 탭 */
    let k = j + 1; while (k < L.length && k < j + 12 && !PR.test(L[k]) && !(TY.test(L[k]) && NUM.test(L[k + 1] || ''))) k++;
    const w = L.slice(j + 1, k).join(' | '), before = L.slice(Math.max(0, i - 3), i).join(' | ');
    const fl = w.match(/([0-9저중고]+)\s*\/\s*(\d+)\s*층/), dir = w.match(/([동서남북]{1,2})향/), d = (before + ' | ' + w).match(/(\d+)\s*동(?![가-힣])/);
    const c = w.match(/확인(?:매물)?\s*(?:\d\d)?(\d{2}\.\d{2}\.\d{2})/) || w.match(/(?:\d\d)?(\d{2}\.\d{2}\.\d{2})\.?\s*확인/);   /* 새 화면 '집주인확인매물 2026.11.03' */
    const ex0 = area(w), ex = ex0 && ex0 >= 15 ? ex0 : null;
    if (!ex && !fl && !c) { i = k - 1; continue; }   /* 면적·층·확인일이 다 없으면 매물 칸이 아님(시세 요약 '매매 12억' 등, 2026-11-03) */
    items.push({ type: ty, price: pr.trim(), ex, fl: fl ? fl[1] : '', tot: fl ? +fl[2] : 0, dir: dir ? dir[1] + '향' : '', spec: w.slice(0, 120), conf: c ? c[1] : '', dong: d ? d[1] : '' });
    i = k - 1;
  }
  /* 단지 이름: 새 화면은 문서 제목 '망월동 미사강변골든센트로 시세/실거래, …'(동 이름 뺌), 옛 화면은 '아파트 / 1541세대' 위 줄 */
  const tm = document.title.match(/^(?:\S+[동읍면리가]\s)?(.+?)\s시세/), hi = L.findIndex(x => /^아파트\s*\/\s*[\d,]+세대/.test(x));
  const nm = (tm ? tm[1] : hi > 0 ? L[hi - 1] : document.title.split(/\s[-|:]\s/)[0]).replace(/[★☆]/g, '').trim();
  let s, msg;
  /* 2026-11-03: 새 화면에서 면적을 1·2·3 으로 잘못 읽어 저장됨 → 절반 넘게 면적을 못 읽으면 저장하지 않고 확인용(매물 주변 글자)을 복사 */
  const miss = items.filter(x => !x.ex).length;
  if (items.length && miss * 2 > items.length) {
    s = '[house-check 면적 확인용]\n' + href + '\n' + document.title + '\n' + items.slice(0, 8).map(x => `${x.type} ${x.price} ⇒ ${x.spec}`).join('\n') + '\n---\n' + L.slice(0, 120).join('\n');
    msg = `매물 ${items.length}건 중 ${miss}건의 면적을 못 읽어 저장하지 않았습니다. 확인용 글자를 복사했으니 Claude 채팅에 붙여넣어 주세요.`;
  } else if (items.length) {
    s = JSON.stringify({ src: 'naver', v: 2, no, nm, at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10), n: items.length, items });
    /* 주소 # 뒤는 서버로 안 감. 팝업이 막히면 복사. 한 줄 북마크라 // 주석 금지 */
    const w = window.open('https://house-check-brown.vercel.app/#ask=' + encodeURIComponent(s), 'house-check');
    if (w) return;
    msg = `호가 ${items.length}건을 복사했습니다. house-check 상세 탭 '붙여넣기'에 넣어 주세요.`;
  } else {
    const i0 = Math.max(0, L.findIndex(x => /매매|전세/.test(x) && /[0-9]/.test(x)) - 8);
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, card = null;
    while ((n = tw.nextNode())) { if (/^\s*(매매|전세)\s*[0-9]/.test(n.nodeValue) || /^\s*(매매|전세)\s*$/.test(n.nodeValue)) { card = n.parentElement; break; } }
    for (let u = 0; card && u < 6 && card.parentElement && card.innerText.length < 120; u++) card = card.parentElement;
    s = '[house-check 확인용 v2]\n' + href + '\n' + document.title + '\n' + L.slice(i0, i0 + 50).join('\n') + '\n---\n'
      + (card ? card.outerHTML.replace(/<(img|svg|path)[^>]*>/g, '').replace(/\s(style|d)="[^"]*"/g, '').slice(0, 3000) : '(매물 칸 없음)');
    msg = '매물을 읽지 못해 확인용 글자를 대신 복사했습니다. Claude 채팅에 붙여넣어 주세요.';
  }
  const done = () => alert(msg);
  if (navigator.clipboard) navigator.clipboard.writeText(s).then(done, () => prompt('복사해서 붙여넣으세요', s)); else prompt('복사해서 붙여넣으세요', s);
} catch (e) { alert('house-check 호가 저장 오류: ' + e.message); } })();
