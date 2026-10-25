/* 웹 화면 저장 동기화: 처음 한 번 '주소?k=비밀문구' 로 열면 이 기기에 기억 → 서버(user_state)의 기록을 읽어 와 화면 기록으로 쓰고,
   바뀔 때마다 서버에 저장(store.set → hcSync). 비밀 문구가 없거나 틀리면 이 기기에만 저장(시안과 같음). build_v2.py --web 이 머리에 넣는다 */
(function () {
  var K = 'hc-key', SYNC = /^v2-(watch2|visits|naver|nmap|area)$/, key = null;
  try { var q = new URLSearchParams(location.search).get('k'); if (q) { localStorage.setItem(K, q); history.replaceState(null, '', location.pathname); } key = localStorage.getItem(K); } catch (e) {}
  var W = window.HC_WEB = { key: key, ok: false };
  if (!key) return;
  function post(k, v) { return fetch('/api/state', { method: 'POST', headers: { 'content-type': 'application/json', 'x-hc-key': key }, body: JSON.stringify({ k: k, v: v }) }); }
  // 2026-10-25: 화면 코드는 data.json 이 온 뒤 돌므로(build_v2 --web 로더) 기록도 같이 비동기로 받아 둔다. 로더가 window.__stateP 를 기다림
  window.__stateP = fetch('/api/state', { headers: { 'x-hc-key': key } }).then(function (r) {
    if (r.status === 401) { W.bad = true; return null; }
    return r.ok ? r.json() : null;
  }).then(function (S) {
    if (!S) return;
    W.ok = true;
    for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (SYNC.test(k) && !(k in S)) post(k, JSON.parse(localStorage.getItem(k))); }   // 서버에 없던 이 기기 기록은 올림
    Object.keys(S).forEach(function (k) { localStorage.setItem(k, JSON.stringify(S[k])); });
  }).catch(function () {});
  var t = {};
  window.hcSync = function (k, v) { if (!W.ok || !SYNC.test(k)) return; clearTimeout(t[k]); t[k] = setTimeout(function () { post(k, v); }, 400); };
  addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.pill.ex').forEach(function (e) { if (/이 기기/.test(e.textContent) && W.ok) e.remove(); });
  });
})();
