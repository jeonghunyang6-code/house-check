// 찾기 탭 '최고가 대비 하락 거래'(2026-11-21 사용자, 아실 '최근 하락'·호갱노노 '하락거래' 참고). HC_KEY 를 아는 요청만.
// 관심 지역(시군구 코드)을 공개 data.json 에 싣지 않으려고 여기서 준다. 최근 30일 계약, 중개·1층 제외, 같은 단지·평형 이전 최고가(prev_high_10k,
// 보관 파일 역대 최고 포함) 대비 5% 이상 싸게(🔧). 하락 비율 큰 순 40건. [단지, 이름, 시군구, 동, 계약일 YYMMDD, 평형, 층, 가격, 이전 최고가, 세대수, 등기 1/0]
const { Client } = require('pg');

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const q = req.query || {}, rcs = String(q.r || '').split(',').filter(x => /^\d{5}$/.test(x)).slice(0, 12);
  const lo = parseInt(q.lo, 10), hi = parseInt(q.hi, 10);
  if (!rcs.length || !(lo >= 30 && hi <= 200 && lo <= hi)) return res.status(400).json({ error: 'q' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query(`SELECT d.apt_seq s, c.apt_name nm, d.region_code rc, c.umd_name umd, to_char(d.contract_date, 'YYMMDD') d, d.area_group ag, d.floor fl,
        d.price_10k p, d.prev_high_10k hi, k.households hh, CASE WHEN d.rgst_date IS NOT NULL THEN 1 ELSE 0 END rg
      FROM deals d JOIN complexes c USING (apt_seq) LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
      WHERE d.region_code = ANY($1) AND d.contract_date >= (now() AT TIME ZONE 'Asia/Seoul')::date - 30 AND NOT d.is_cancelled AND d.deal_type <> '직거래'
        AND d.floor <> 1 AND d.area_group BETWEEN $2 AND $3 AND d.prev_high_10k IS NOT NULL AND d.price_10k <= d.prev_high_10k * 0.95
      ORDER BY (d.prev_high_10k - d.price_10k)::float / d.prev_high_10k DESC LIMIT 40`, [rcs, lo, hi]);
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ d: r.rows.map(x => [x.s, x.nm, x.rc, x.umd, x.d, x.ag, x.fl, x.p, x.hi, x.hh, x.rg]) });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
