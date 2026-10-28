// 상세 탭 최근 실거래 1년 보기·호가 그래프 실거래 ◆ (2026-10-28 사용자 요청). HC_KEY 를 아는 요청만, 단지 하나씩.
// data.json 에 1년치를 넣으면 모든 단지면 너무 크고, 관심 단지만 넣으면 공개 파일에 관심 단지 목록이 드러나서 여기서 준다.
// 기준 시세 주별 계산(60일 → 90 → 180일)에 쓰도록 1년 + 180일. [계약일 YYMMDD, 평형, 층, 가격(만원), 직거래 1/0]
const { Client } = require('pg');

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const s = String((req.query && req.query.s) || '');
  if (!/^\d{5}-\d{1,8}$/.test(s)) return res.status(400).json({ error: 's' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query(`SELECT to_char(contract_date, 'YYMMDD') d, area_group ag, floor fl, price_10k p, CASE WHEN deal_type = '직거래' THEN 1 ELSE 0 END dt
      FROM deals WHERE apt_seq = $1 AND NOT is_cancelled AND contract_date >= (now() AT TIME ZONE 'Asia/Seoul')::date - 545
      AND area_group BETWEEN 40 AND 135 ORDER BY contract_date DESC`, [s]);
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ d: r.rows.map(x => [x.d, x.ag, x.fl, x.p, x.dt]) });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
