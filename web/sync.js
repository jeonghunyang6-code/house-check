/* 웹 화면 저장 동기화: 처음 한 번 '주소?k=비밀문구' 로 열면 이 기기에 기억 → 서버(user_state)의 기록을 읽어 와 화면 기록으로 쓰고,
   바뀔 때마다 서버에 저장(store.set → hcSync). 비밀 문구가 없거나 틀리면 이 기기에만 저장(시안과 같음). build_v2.py --web 이 본문 앞에 넣는다 */
(function () {
  var K = 'hc-key', SYNC = /^v2-(watch2|visits|naver|nmap|area)$/, key = null;
  try { var q = new URLSearchParams(location.search).get('k'); if (q) { localStorage.setItem(K, q); history.replaceState(null, '', location.pathname); } key = localStorage.getItem(K); } catch (e) {}
  var W = window.HC_WEB = { key: key, ok: false };
  if (!key) return;
  function post(k, v) { return fetch('/api/state', { method: 'POST', headers: { 'content-type': 'application/json', 'x-hc-key': key }, body: JSON.stringify({ k: k, v: v }) }); }
  try {
    var x = new XMLHttpRequest(); x.open('GET', '/api/state', false); x.setRequestHeader('x-hc-key', key); x.send();   // 화면 그리기 전에 기록이 있어야 해서 동기 요청
    if (x.status === 200) {
      var S = JSON.parse(x.responseText); W.ok = true;
      for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (SYNC.test(k) && !(k in S)) post(k, JSON.parse(localStorage.getItem(k))); }   // 서버에 없던 이 기기 기록은 올림
      Object.keys(S).forEach(function (k) { localStorage.setItem(k, JSON.stringify(S[k])); });
    } else if (x.status === 401) { W.bad = true; }
  } catch (e) {}
  var t = {};
  window.hcSync = function (k, v) { if (!W.ok || !SYNC.test(k)) return; clearTimeout(t[k]); t[k] = setTimeout(function () { post(k, v); }, 400); };
  addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.pill.ex').forEach(function (e) { if (/이 기기/.test(e.textContent) && W.ok) e.remove(); });
  });
})();
