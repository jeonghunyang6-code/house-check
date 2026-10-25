/* 네이버 부동산 '이 화면 호가 저장' 북마크 버튼 (2026-10-21 사용자 결정).
   쓰는 법: 네이버 부동산(new.land.naver.com)에서 단지를 열고 왼쪽 매물 목록을 끝까지 내려 다 불러온 뒤 북마크를 누른다.
   → 화면에 보이는 매물(거래 방식·가격·면적·층·향·동·확인일)을 읽어 house-check 사이트를 새 탭으로 열며 바로 저장(2026-10-25).
     팝업이 막히면 예전처럼 클립보드에 복사 → 상세 탭 '붙여넣기'.
   하는 일: 이미 화면에 뜬 글자만 읽는다. 네이버 서버를 따로 부르지 않고, 다른 페이지를 돌지 않는다(자동 수집·위장 없음).
   읽는 순서: ① 매물 칸(.item 안 .price_line·.spec·.item_title) ② 안 되면 화면 글자 줄 단위.
   2026-10-21 첫 사용에서 0건: 실제 화면은 '매매'·'15억'이 붙어 읽히고(매매15억) 면적이 'm²' 로 적힘 → 둘 다 허용.
   그래도 0건이면 확인용 글자(목록 앞부분)를 대신 복사한다 → 채팅에 붙여넣어 규칙을 고친다.
   북마크 주소로 쓰는 한 줄은 tools/pc/README.md (만드는 법도 거기) */
(() => {
  const T = (el) => (el ? el.textContent : '').replace(/\s+/g, ' ').trim();
  const no = (location.pathname.match(/complexes\/(\d+)/) || [])[1] || null;
  const PRICE = /^(매매|전세|월세)\s*([0-9][0-9억,\s/]*)$/;
  const SPEC = /(㎡|m²|m2)/;
  let items = [];
  const cards = [...document.querySelectorAll('.item')].filter(el => el.querySelector('.price_line'));
  for (const el of cards) {
    const ty = T(el.querySelector('.price_line .type')), pr = T(el.querySelector('.price_line .price'));
    const p = (ty + ' ' + pr).match(PRICE);
    if (!p) continue;
    const spec = [...el.querySelectorAll('.info_area .spec, .spec')].map(T).find(s => SPEC.test(s) && /층/.test(s)) || '';
    const c = T(el).match(/확인매물\s*(\d{2}\.\d{2}\.\d{2})/), d = T(el.querySelector('.item_title')).match(/(\d+)동/);
    items.push({ type: p[1], price: p[2].trim(), spec, conf: c ? c[1] : '', dong: d ? d[1] : '' });
  }
  const L = document.body.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  if (!items.length) {
    for (let i = 0; i < L.length; i++) {
      const p = L[i].match(PRICE);
      if (!p) continue;
      let spec = '', conf = '', dong = '';
      for (let k = Math.max(0, i - 3); k < Math.min(L.length, i + 8); k++) {
        if (k > i && PRICE.test(L[k])) break;
        if (k < i) { const d = L[k].match(/(\d+)동$/); if (d) dong = d[1]; }
        if (k > i && !spec && SPEC.test(L[k]) && /층/.test(L[k])) spec = L[k];
        if (k > i && !conf) { const c = L[k].match(/확인매물\s*(\d{2}\.\d{2}\.\d{2})/); if (c) conf = c[1]; }
      }
      items.push({ type: p[1], price: p[2].trim(), spec, conf, dong });
    }
  }
  let s, msg;
  /* 단지 이름: '아파트 / 1541세대 / …' 줄 바로 위 줄(★ 뺌). 사이트가 처음 보는 단지 번호를 이름으로 잇는다 */
  const hi = L.findIndex(x => /^아파트\s*\/\s*[\d,]+세대/.test(x)), nm = hi > 0 ? L[hi - 1].replace(/[★☆]/g, '').trim() : '';
  if (items.length) {
    s = JSON.stringify({ src: 'naver', no, nm, at: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10), n: items.length, items });
    /* 2026-10-25: 복사·붙여넣기 대신 사이트를 열어 바로 저장(주소 # 뒤는 서버로 안 감). 팝업이 막히면 예전처럼 복사. 한 줄 북마크라 // 주석 금지 */
    const w = window.open('https://house-check-brown.vercel.app/#ask=' + encodeURIComponent(s), 'house-check');
    if (w) return;
    msg = `호가 ${items.length}건을 복사했습니다. house-check 상세 탭 '붙여넣기'에 넣어 주세요.`;
  } else {
    const i0 = Math.max(0, L.findIndex(x => /확인매물/.test(x)) - 12), first = cards[0] || document.querySelector('.item');
    s = '[house-check 확인용]\n' + location.pathname + '\n' + L.slice(i0, i0 + 40).join('\n') + '\n---\n' + (first ? first.outerHTML.replace(/<img[^>]*>/g, '').slice(0, 2500) : '(item 없음)');
    msg = '매물을 읽지 못해 확인용 글자를 대신 복사했습니다. Claude 채팅에 붙여넣어 주세요.';
  }
  const done = () => alert(msg);
  if (navigator.clipboard) navigator.clipboard.writeText(s).then(done, () => prompt('복사해서 붙여넣으세요', s)); else prompt('복사해서 붙여넣으세요', s);
})();
