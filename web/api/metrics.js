// 상세 탭 '작가 기준 점검'(2026-11-21). HC_KEY 를 아는 요청만, 단지 하나씩(관심 단지 목록을 공개 data.json 에 싣지 않으려고).
// complex_metrics 의 B2 전고점·저점, B6 상대강도, E2 주변 시세 위치, E3 바로 위 급지(첫 단지 이름), C6 거래 적은 이유
// + C12 3년 비교(2026-11-28): chg_36m·region_chg_36m, 같은 생활권·같은 면적군 이웃 표 nb3 [이름, 3년 전, 지금, 이 단지 여부], 기간 w3
const { Client } = require('pg');

const NB_MAX = 12;   // 이웃 표 최대 줄 수(이 단지 포함). 생활권이 넓으면 지금 시세가 가까운 순

module.exports = async (req, res) => {
  if (!process.env.HC_KEY || req.headers['x-hc-key'] !== process.env.HC_KEY) return res.status(401).json({ error: 'key' });
  const s = String((req.query && req.query.s) || '');
  if (!/^\d{5}-\d{1,8}$/.test(s)) return res.status(400).json({ error: 's' });
  const db = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await db.connect();
  try {
    const r = await db.query(`SELECT m.area_group, m.peak_10k, m.peak_month, m.trough_10k, m.trough_month, m.chg_12m, m.region_chg_12m, m.rel_strength,
        m.e2_ratio, m.e2_n, m.e2_basis, m.e3_target_10k, c3.apt_name AS e3_name, m.turnover_pct, m.c6_band_turn, m.c6_reason,
        m.chg_36m, m.region_chg_36m
      FROM complex_metrics m LEFT JOIN complexes c3 ON c3.apt_seq = split_part(m.e3_seqs, ',', 1)
      WHERE m.apt_seq = $1`, [s]);
    const ags = r.rows.filter(x => x.chg_36m != null).map(x => x.area_group);
    if (ags.length) {
      const nb = await db.query(`SELECT m.area_group, c.apt_name, m.y3_10k, m.m6_10k, m.apt_seq = $1 AS me
        FROM complex_metrics m JOIN complexes c USING (apt_seq)
        WHERE c.lifezone_id = (SELECT lifezone_id FROM complexes WHERE apt_seq = $1) AND m.area_group = ANY($2::int[]) AND m.chg_36m IS NOT NULL`, [s, ags]);
      const w = await db.query(`SELECT min(from_month) AS f, min(to_month) AS t FROM deal_y3`);
      const f = w.rows[0] && w.rows[0].f, t = w.rows[0] && w.rows[0].t;
      const yymm = (ym, k) => { if (!ym) return null; let y = +ym.slice(0, 4), m = +ym.slice(4) + k; while (m > 12) { y++; m -= 12; } return String(y).slice(2) + String(m).padStart(2, '0'); };
      const w3 = f ? [yymm(f, 0), yymm(t, 0), yymm(f, 36), yymm(t, 36)] : null;
      for (const row of r.rows) {
        if (row.chg_36m == null) continue;
        const all = nb.rows.filter(x => x.area_group === row.area_group), me = all.find(x => x.me);
        const ref = me ? me.m6_10k : 0;
        const pick = all.sort((a, b) => Math.abs(a.m6_10k - ref) - Math.abs(b.m6_10k - ref)).slice(0, NB_MAX);
        if (me && !pick.includes(me)) pick[pick.length - 1] = me;
        row.nb3 = pick.sort((a, b) => b.m6_10k - a.m6_10k).map(x => [x.apt_name, x.y3_10k, x.m6_10k, x.me ? 1 : 0]);
        row.w3 = w3;
      }
    }
    res.setHeader('Cache-Control', 'private, max-age=3600');
    return res.status(200).json({ d: r.rows });
  } catch (e) {
    return res.status(500).json({ error: 'db' });
  } finally {
    await db.end();
  }
};
