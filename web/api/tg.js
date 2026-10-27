// 텔레그램 봇 웹훅: 사용자 대화방에서 단지 이름을 보내면 요약을 답한다(lib/tgreply.js). site.yml 이 배포 뒤 setWebhook.
// 확인: 텔레그램이 보내는 비밀 헤더 = sha256(HC_KEY) 앞 48자, 그리고 대화 번호 = DB user_state 'tg_chat'(다른 사람 메시지는 무시)
// 환경 변수: DATABASE_URL, HC_KEY, TELEGRAM_BOT_TOKEN
const crypto = require('crypto');
const { Client } = require('pg');
const { reply } = require('../lib/tgreply');

module.exports = async (req, res) => {
  const want = process.env.HC_KEY && crypto.createHash('sha256').update(process.env.HC_KEY).digest('hex').slice(0, 48);
  if (req.method !== 'POST' || !want || req.headers['x-telegram-bot-api-secret-token'] !== want) return res.status(401).end();
  const msg = (req.body || {}).message;
  if (!msg || !msg.text || !process.env.TELEGRAM_BOT_TOKEN) return res.status(200).end();
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const c = (await db.query("SELECT v #>> '{}' v FROM user_state WHERE k = 'tg_chat'")).rows[0];
    if (!c || String(c.v) !== String(msg.chat.id)) return res.status(200).end();
    const site = ((await db.query("SELECT v #>> '{}' v FROM user_state WHERE k = 'site_url'")).rows[0] || {}).v;
    let text;
    try { text = await reply((sql, p) => db.query(sql, p), msg.text, site); } catch (e) { text = '찾는 중 오류가 났습니다. 잠시 뒤 다시 보내 주세요.'; }
    await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`, { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: msg.chat.id, text, parse_mode: 'HTML', disable_web_page_preview: true }) });
    return res.status(200).end();
  } finally {
    await db.end();
  }
};
