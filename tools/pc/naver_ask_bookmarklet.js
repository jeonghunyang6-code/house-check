/* 네이버 부동산 '이 화면 호가 저장' 북마크 버튼 (2026-10-21 사용자 결정).
   쓰는 법: 네이버 부동산(new.land.naver.com)에서 단지를 열고 왼쪽 매물 목록을 끝까지 내려 다 불러온 뒤 북마크를 누른다.
   → 화면에 보이는 매물(거래 방식·가격·면적·층·향·동·확인일)을 읽어 클립보드에 복사 → house-check 상세 탭 '붙여넣기'.
   하는 일: 이미 화면에 뜬 글자만 읽는다. 네이버 서버를 따로 부르지 않고, 다른 페이지를 돌지 않는다(자동 수집·위장 없음).
   화면 글자 모양(예: '매매 15억', '아파트·116B/84㎡, 22/26층, 남동향', '확인매물 26.10.19.')은 2026-10-21 사용자 화면 캡처 기준.
   네이버 화면이 바뀌면 읽는 규칙을 고쳐야 한다. 북마크 주소로 쓰는 한 줄은 tools/pc/README.md */
(() => {
  const L = document.body.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const no = (location.pathname.match(/complexes\/(\d+)/) || [])[1] || null;
  const items = [];
  for (let i = 0; i < L.length; i++) {
    const p = L[i].match(/^(매매|전세|월세)\s+([0-9억,\s/]+)$/);
    if (!p) continue;
    let spec = '', conf = '', dong = '';
    for (let k = Math.max(0, i - 3); k < Math.min(L.length, i + 8); k++) {
      if (k > i && !spec && /㎡/.test(L[k]) && /층/.test(L[k])) spec = L[k];
      if (k > i && !conf) { const c = L[k].match(/확인매물\s*(\d{2}\.\d{2}\.\d{2})/); if (c) conf = c[1]; }
      if (k < i) { const d = L[k].match(/(\d+)동$/); if (d) dong = d[1]; }
      if (k > i && /^(매매|전세|월세)\s/.test(L[k])) break;
    }
    items.push({ type: p[1], price: p[2].trim(), spec, conf, dong });
  }
  const data = { src: 'naver', no, at: new Date().toISOString().slice(0, 10), n: items.length, items };
  const s = JSON.stringify(data);
  const done = () => alert(`호가 ${items.length}건을 복사했습니다. house-check 상세 탭 '붙여넣기'에 넣어 주세요.` + (items.length ? '' : '\n(0건이면 왼쪽 매물 목록이 열려 있는지 확인)'));
  if (navigator.clipboard) navigator.clipboard.writeText(s).then(done, () => prompt('복사해서 붙여넣으세요', s)); else prompt('복사해서 붙여넣으세요', s);
})();
