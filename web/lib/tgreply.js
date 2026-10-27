// 텔레그램에서 단지 이름을 보내면 요약을 답한다(api/tg.js 가 부름, 2026-10-27 사용자 요청). DB 질의는 q(sql, params) 로 받아 시험하기 쉽게.
// 답: 기준 시세(84㎡에 가장 가까운 평형)·전세가율·최근 실거래 3건(없으면 분양권·입주권)·저장 호가(84㎡대). 판정 없이 숫자만.
const norm = (s) => String(s || '').toLowerCase().replace(/[\s()·.\-]/g, '');
const eok = (v) => v == null ? '–' : v >= 10000 ? (v / 10000).toFixed(2).replace(/\.?0+$/, '') + '억' : Math.round(v).toLocaleString() + '만';
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const HELP = '단지 이름을 보내 주세요(예: 고덕그라시움, 골든센트로). 관심 단지를 먼저 찾습니다.';

function jsonOf(v) { if (v == null) return null; if (typeof v === 'string') { try { return JSON.parse(v); } catch (e) { return null; } } return v; }

function askLine(asks, seq) {
  const byDate = (asks || {})[seq] || {}, dates = Object.keys(byDate).sort();
  if (!dates.length) return null;
  const d = dates[dates.length - 1];
  const ps = (byDate[d] || []).filter(x => x.t === '매매' && x.ex && +x.ex >= 75 && +x.ex < 100).map(x => x.p).sort((a, b) => a - b);
  return ps.length ? `🏷️ 저장 호가 84㎡대 ${ps.length}개 · 중간 ${eok(ps[(ps.length - 1) >> 1])} · 최저 ${eok(ps[0])} (${d.slice(5).replace('-', '/')})` : null;
}

async function find(q, text) {
  const k = norm(text);
  if (k.length < 2) return { list: [] };
  const st = await q("SELECT k, v FROM user_state WHERE k IN ('v2-watch2', 'v2-naver')");
  const S = Object.fromEntries(st.rows.map(r => [r.k, jsonOf(r.v)]));
  const watch = Array.isArray(S['v2-watch2']) ? S['v2-watch2'] : [];
  const r = await q(`SELECT c.apt_seq, c.apt_name, c.umd_name, k.households hh,
      regexp_replace(lower(c.apt_name), '[[:space:]()·.-]', '', 'g') = $1 OR regexp_replace(lower(coalesce(k.kapt_name, '')), '[[:space:]()·.-]', '', 'g') = $1 AS exact
    FROM complexes c LEFT JOIN kapt_complexes k USING (kapt_code)
    WHERE (regexp_replace(lower(c.apt_name), '[[:space:]()·.-]', '', 'g') LIKE '%' || $1 || '%'
        OR regexp_replace(lower(coalesce(k.kapt_name, '')), '[[:space:]()·.-]', '', 'g') LIKE '%' || $1 || '%')
      AND NOT EXISTS (SELECT 1 FROM complex_successor s WHERE s.old_seq = c.apt_seq)
    ORDER BY (c.apt_seq = ANY($2::text[])) DESC, exact DESC, k.households DESC NULLS LAST LIMIT 6`, [k, watch]);
  return { list: r.rows, watch, asks: S['v2-naver'] };
}

async function summary(q, row, watch, asks) {
  const seq = row.apt_seq;
  const m = (await q(`SELECT area_group ag, ref_10k, jeonse_10k, jeonse_ratio::float ratio FROM complex_metrics
    WHERE apt_seq = $1 AND ref_10k IS NOT NULL ORDER BY abs(area_group - 84) LIMIT 1`, [seq])).rows[0];
  let d = (await q(`SELECT contract_date::text d, area_m2::float a, floor, price_10k p, '' k FROM deals WHERE apt_seq = $1 AND NOT is_cancelled
    ORDER BY contract_date DESC LIMIT 3`, [seq])).rows;
  if (!d.length) d = (await q(`SELECT contract_date::text d, area_m2::float a, floor, price_10k p, kind k FROM right_deals WHERE apt_seq = $1 AND NOT is_cancelled
    ORDER BY contract_date DESC LIMIT 3`, [seq])).rows;
  const out = [`🏠 <b>${esc(row.apt_name)}</b>${watch.includes(seq) ? ' ♥' : ''} · ${esc(row.umd_name || '')}${row.hh ? ` · ${(+row.hh).toLocaleString()}세대` : ''}`];
  if (m) out.push(`💰 ${m.ag}㎡ 기준 ${eok(m.ref_10k)}` + (m.ratio ? ` · 전세 ${eok(m.jeonse_10k)}(${Math.round(m.ratio)}%)` : ''));
  else out.push('💰 기준 시세 없음(거래가 적거나 등기 전)');
  d.forEach(x => out.push(`🧾 ${x.d.slice(2).replace(/-/g, '.')} ${Math.round(x.a)}㎡ ${x.floor}층 <b>${eok(x.p)}</b>${x.k ? ' · ' + x.k : ''}`));
  const a = askLine(asks, seq); if (a) out.push(a);
  return out.join('\n');
}

async function reply(q, text, site) {
  const t = String(text || '').trim();
  if (!t || /^\/(start|help)|^도움/.test(t)) return HELP;
  const { list, watch, asks } = await find(q, t);
  if (!list.length) return `'${esc(t)}' 단지를 찾지 못했습니다. 이름 일부만 보내도 됩니다(예: 그라시움).`;
  const one = list.length === 1 || list[0].exact || (watch.includes(list[0].apt_seq) && !watch.includes((list[1] || {}).apt_seq));
  if (!one) return '여러 단지가 있습니다. 더 정확히 보내 주세요:\n' + list.map(r => `• ${esc(r.apt_name)} (${esc(r.umd_name || '')})`).join('\n');
  return (await summary(q, list[0], watch, asks)) + (site ? `\n${site}` : '');
}

module.exports = { reply, norm, askLine, HELP };
