// 배포 전 화면 점검(site.yml, 2026-10-27 사용자 요청): build_v2 --web 결과 폴더를 로컬로 열어 시장 → 찾기 → 관심 → 상세 → 계획을 눌러 보고,
// 화면 오류(pageerror)나 빈 탭이 있으면 1 로 끝나 배포를 멈춘다(어제 사이트가 그대로 남음).
//   NODE_PATH=<playwright 있는 node_modules> node tools/prototype/smoke.js house-check
// 네이버 지도·글꼴은 막는다(지도는 그림 지도로 대신 그려지는지까지 본다). 개인 기록 API 는 401(문구 없음)처럼 둔다.
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');

const dir = path.resolve(process.argv[2] || 'house-check');
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.js': 'text/javascript' };
const srv = http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split('?')[0]);
  if (u.startsWith('/api/')) { r.statusCode = 401; return r.end('{}'); }
  const f = path.join(dir, u === '/' ? 'index.html' : u);
  if (!f.startsWith(dir) || !fs.existsSync(f)) { r.statusCode = 404; return r.end(); }
  r.setHeader('content-type', TYPES[path.extname(f)] || 'application/octet-stream'); r.end(fs.readFileSync(f));
});

// 탭마다 '비어 있으면 안 되는' 칸
const TABS = [['home', ['#hAsof', '#sigs', '#wkRank']], ['find', ['#cCount', '#cList']], ['watch', ['#wList']], ['daily', ['#dHead', '#dDeals']], ['plan', ['#fundKpis']]];

(async () => {
  await new Promise(ok => srv.listen(0, ok));
  const url = `http://127.0.0.1:${srv.address().port}/`;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 400, height: 900 } });
  const bad = [];
  p.on('pageerror', e => bad.push('화면 오류: ' + String(e).slice(0, 300)));
  await p.route(/oapi\.map\.naver\.com|fonts\.(googleapis|gstatic)\.com/, rt => rt.abort());
  try {
    await p.goto(url);
    await p.waitForFunction(() => document.body.classList.contains('hc-b') || document.body.classList.contains('hc-fail'), null, { timeout: 60000 });
    if (await p.evaluate(() => document.body.classList.contains('hc-fail'))) bad.push('데이터를 불러오지 못함');
    for (const [t, sels] of TABS) {
      await p.click(`#tabbar button[data-t="${t}"]`); await p.waitForTimeout(t === 'daily' ? 1500 : 400);
      for (const s of sels) {
        const n = await p.evaluate(sel => { const e = document.querySelector(sel); return e ? e.textContent.trim().length : -1; }, s);
        if (n <= 0) bad.push(`${t} 탭 ${s} ${n < 0 ? '없음' : '비어 있음'}`);
      }
    }
    const map = await p.evaluate(() => !document.getElementById('dMap').hasAttribute('hidden') || !document.getElementById('dNmap').hidden);
    if (!map) bad.push('상세 탭 지도가 안 보임');
  } catch (e) {
    bad.push('점검 중 멈춤: ' + String(e).slice(0, 300));
  }
  await b.close(); srv.close();
  if (bad.length) { console.error('화면 점검 실패 → 배포하지 않음\n' + bad.join('\n')); process.exit(1); }
  console.log('화면 점검 통과(시장·찾기·관심·상세·계획)');
})();
