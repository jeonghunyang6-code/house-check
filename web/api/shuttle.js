// 회사 셔틀 정류장(2026-11-26). 회사 내부 자료 → HC_KEY 를 아는 요청만, 읽기 전용, 캐시·로그 없음.
// o = [이름, 위도, 경도, 노선, 탑승, 도착], h = [이름, 위도, 경도, 노선, [출발 시]]
const crypto = require('crypto');
const { Client } = require('pg');

const same = (a, b) => { const x = Buffer.from(String(a || '')), y = Buffer.from(String(b || '')); return x.length === y.length && crypto.timingSafeEqual(x, y); };

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'private, no-store');   // 브라우저·Vercel 어디에도 남기지 않음
  if (req.method !== 'GET') return res.status(405).json({ error: 'method' });
  if (!process.env.HC_KEY || !same(req.headers['x-hc-key'], process.env.HC_KEY)) return res.status(401).json({ error: 'key' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query('SELECT kind, name, lat, lng, route, t_board, t_arrive, hours FROM shuttle_stops');
    const o = [], h = [];
    r.rows.forEach(x => x.kind === 'o' ? o.push([x.name, x.lat, x.lng, x.route, x.t_board, x.t_arrive]) : h.push([x.name, x.lat, x.lng, x.route, String(x.hours || '').split(',').filter(Boolean)]));
    return res.status(200).json({ o, h });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
