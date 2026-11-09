// 상세 탭 최근 실거래 6개월 보기·호가 그래프 실거래 ◆ (2026-10-28 사용자 요청). HC_KEY 를 아는 요청만, 단지 하나씩.
// data.json 에 6개월치를 넣으면 모든 단지면 너무 크고, 관심 단지만 넣으면 공개 파일에 관심 단지 목록이 드러나서 여기서 준다.
// 기준 시세 주별 계산(60일 → 90 → 180일)에 쓰도록 6개월 + 180일. [계약일 YYMMDD, 평형, 층, 가격(만원), 직거래 1/0,
//  해제 1/0, 해제일, 등기일, 처음 확인한 날(우리 수집, 2026-10-12~; 국토부 신고일 아님), 전용면적㎡] — 뒤 다섯 칸은 2026-11-09 평형별 거래 근거(해제도 목록에 남김)
const { Client } = require('pg');

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const s = String((req.query && req.query.s) || '');
  if (!/^\d{5}-\d{1,8}$/.test(s)) return res.status(400).json({ error: 's' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query(`SELECT to_char(contract_date, 'YYMMDD') d, area_group ag, floor fl, price_10k p, CASE WHEN deal_type = '직거래' THEN 1 ELSE 0 END dt,
      CASE WHEN is_cancelled THEN 1 ELSE 0 END c, coalesce(to_char(cancel_date, 'YYMMDD'), '') cd, coalesce(to_char(rgst_date, 'YYMMDD'), '') rg,
      coalesce(to_char(first_seen_date, 'YYMMDD'), '') fs, area_m2::float a
      FROM deals WHERE apt_seq = $1 AND contract_date >= (now() AT TIME ZONE 'Asia/Seoul')::date - 370
      AND area_group BETWEEN 40 AND 135 ORDER BY contract_date DESC`, [s]);
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ d: r.rows.map(x => [x.d, x.ag, x.fl, x.p, x.dt, x.c, x.cd, x.rg, x.fs, x.a]) });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
