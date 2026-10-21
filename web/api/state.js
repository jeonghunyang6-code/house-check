// 개인 기록 읽기·쓰기 (user_state, 0068). HC_KEY 를 아는 요청만. Vercel 서버 함수(Node)
// 환경 변수: DATABASE_URL(Supabase), HC_KEY(사용자가 정한 비밀 문구) — site.yml 이 배포 때 넣는다
const { Client } = require('pg');
const KEYS = /^v2-(watch2|visits|naver|nmap|area)$/;

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    if (req.method === 'GET') {
      const r = await db.query("SELECT k, v FROM user_state WHERE k LIKE 'v2-%'");
      return res.status(200).json(Object.fromEntries(r.rows.map(x => [x.k, x.v])));
    }
    if (req.method === 'POST') {
      const { k, v } = req.body || {};
      if (!KEYS.test(k || '') || v === undefined) return res.status(400).json({ error: 'k' });
      const body = JSON.stringify(v);
      if (body.length > 2e6) return res.status(413).json({ error: 'size' });
      await db.query('INSERT INTO user_state (k, v) VALUES ($1, $2::jsonb) ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()', [k, body]);
      return res.status(200).json({ ok: true });
    }
    return res.status(405).end();
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
