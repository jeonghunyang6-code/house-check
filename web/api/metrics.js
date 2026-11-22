// 상세 탭 '작가 기준 점검'(2026-11-21). HC_KEY 를 아는 요청만, 단지 하나씩(관심 단지 목록을 공개 data.json 에 싣지 않으려고).
// complex_metrics 의 B2 전고점·저점, B6 상대강도, E2 주변 시세 위치, E3 바로 위 급지(첫 단지 이름), C6 거래 적은 이유
const { Client } = require('pg');

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const s = String((req.query && req.query.s) || '');
  if (!/^\d{5}-\d{1,8}$/.test(s)) return res.status(400).json({ error: 's' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query(`SELECT m.area_group, m.peak_10k, m.peak_month, m.trough_10k, m.trough_month, m.chg_12m, m.region_chg_12m, m.rel_strength,
        m.e2_ratio, m.e2_n, m.e2_basis, m.e3_target_10k, c3.apt_name AS e3_name, m.turnover_pct, m.c6_band_turn, m.c6_reason
      FROM complex_metrics m LEFT JOIN complexes c3 ON c3.apt_seq = split_part(m.e3_seqs, ',', 1)
      WHERE m.apt_seq = $1`, [s]);
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ d: r.rows });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
