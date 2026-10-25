"""분양권·입주권 거래 수집 (collector/sources/molit.py fetch_rights → right_deals, 0069). daily.yml 이 최근 3개월을 다시 받는다.

    python -m jobs.right_deals                 # 수도권 전체, 이번 달 포함 최근 3개월
    python -m jobs.right_deals --months 24 --backfill   # 처음 한 번: 2년치. 새로 넣는 행의 first_seen_date = 계약일(알림에 '새 거래'로 안 뜨게)
    python -m jobs.right_deals --regions 11740 --months 6

같은 달·같은 값 거래가 두 건 이상이면(실제로 있음) 순번(#1, #2)으로 구분한다. 받은 뒤 단지 연결(apt_seq):
① 같은 시군구에서 이름(우리 단지 이름 또는 K-apt 이름, 띄어쓰기·괄호·가운뎃점 무시)이 같으면 ② 같은 동·지번이면. 그래도 못 붙인 거래는 분양 단지(presale_complexes, 0070)로 묶어 pc_seq 를 단다(입주 전 신축도 찾고 ♡).
"""

from __future__ import annotations

import argparse
import sys
import difflib
import re
from collections import Counter
from datetime import date

from collector.db import Db, DbError, connect, lit, select
from collector.regions import REGIONS
from collector.sources import molit as M

NORM = "regexp_replace(lower({}), '[[:space:]()·.-]', '', 'g')"


def months_back(today: date, n: int) -> list[str]:
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out


def keyed(rows: list[M.RightDeal]) -> list[tuple[str, M.RightDeal]]:
    seen: Counter = Counter()
    out = []
    for r in rows:
        seen[r.base_key] += 1
        out.append((f"{r.base_key}#{seen[r.base_key]}", r))
    return out


def save(db: Db, rows: list[tuple[str, M.RightDeal]], backfill: bool = False) -> None:
    today = "(now() AT TIME ZONE 'Asia/Seoul')::date"
    for i in range(0, len(rows), 500):
        vals = ", ".join(
            f"({lit(k)}, {lit(r.region_code)}, {lit(r.apt_name)}, {lit(r.umd_name)}, {lit(r.jibun)}, {lit(r.contract_date)}, {r.area_m2}, "
            f"{r.area_group}, {lit(r.floor)}, {r.price_10k}, {lit(r.kind)}, {lit(r.deal_type)}, {lit(r.is_cancelled)}, {lit(r.cancel_date)}, "
            f"{lit(r.contract_date) if backfill else today})"
            for k, r in rows[i:i + 500])
        db.query("INSERT INTO right_deals (deal_key, region_code, apt_name, umd_name, jibun, contract_date, area_m2, area_group, floor, price_10k, "
                 "kind, deal_type, is_cancelled, cancel_date, first_seen_date) VALUES " + vals
                 + " ON CONFLICT (deal_key) DO UPDATE SET is_cancelled = EXCLUDED.is_cancelled, cancel_date = EXCLUDED.cancel_date, "
                   "last_seen_date = (now() AT TIME ZONE 'Asia/Seoul')::date;")


def link(db: Db) -> None:
    n = NORM.format
    db.query(f"""UPDATE right_deals r SET apt_seq = x.apt_seq FROM (
  SELECT DISTINCT ON (r2.deal_key) r2.deal_key, c.apt_seq FROM right_deals r2
  JOIN complexes c ON c.region_code = r2.region_code
  LEFT JOIN kapt_complexes k ON k.kapt_code = c.kapt_code
  WHERE r2.apt_seq IS NULL AND ({n('c.apt_name')} = {n('r2.apt_name')} OR {n('k.kapt_name')} = {n('r2.apt_name')})
  ORDER BY r2.deal_key, c.build_year DESC NULLS LAST) x
WHERE r.deal_key = x.deal_key;
UPDATE right_deals r SET apt_seq = x.apt_seq FROM (
  SELECT DISTINCT ON (r2.deal_key) r2.deal_key, c.apt_seq FROM right_deals r2
  JOIN complexes c ON c.region_code = r2.region_code AND c.umd_name = r2.umd_name AND c.jibun = r2.jibun
  WHERE r2.apt_seq IS NULL AND r2.jibun <> '' ORDER BY r2.deal_key, c.build_year DESC NULLS LAST) x
WHERE r.deal_key = x.deal_key;""")
    # 단지 목록에 없는 거래 → 분양 단지(0070). 시군구 + 정규화 이름으로 묶고, 이름은 가장 최근 표기
    db.query(f"""INSERT INTO presale_complexes (pc_seq, region_code, nkey, apt_name, umd_name, jibun)
SELECT DISTINCT ON (region_code, nk) 'P' || region_code || '-' || substr(md5(nk), 1, 6), region_code, nk, apt_name, umd_name, jibun
FROM (SELECT *, {n('apt_name')} nk FROM right_deals WHERE apt_seq IS NULL AND pc_seq IS NULL) u
ORDER BY region_code, nk, contract_date DESC
ON CONFLICT (region_code, nkey) DO NOTHING;
UPDATE right_deals r SET pc_seq = p.pc_seq FROM presale_complexes p
WHERE r.pc_seq IS NULL AND r.apt_seq IS NULL AND p.region_code = r.region_code AND p.nkey = {n('r.apt_name')};
UPDATE presale_complexes p SET apt_seq = x.apt_seq FROM (
  SELECT pc_seq, max(apt_seq) apt_seq FROM right_deals WHERE pc_seq IS NOT NULL AND apt_seq IS NOT NULL GROUP BY 1) x
WHERE p.pc_seq = x.pc_seq AND p.apt_seq IS DISTINCT FROM x.apt_seq;""")


def _norm(x: str | None) -> str:
    return re.sub(r"[\s()·.\-]", "", (x or "").lower())


def _nums(x: str) -> set[str]:
    """단지 번호(숫자·로마 숫자). 제일풍경채 검단Ⅰ/Ⅲ, A-3/A-4블록 처럼 번호만 다른 단지를 붙이지 않으려고."""
    return set(re.findall(r"\d+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]", x.upper()))   # lower() 가 Ⅰ→ⅰ 로 바꾸므로 다시 대문자로


def match_presale(db: Db) -> int:
    """분양 단지(house_no 없는 것) ↔ 청약홈 분양정보. ① 같은 시군구, 이름 포함 ② 같은 시도·주소에 동 이름, 이름 유사도 🔧0.6+, 번호 같음."""
    pcs = select(db, "SELECT pc_seq, apt_name, region_code, umd_name FROM presale_complexes WHERE house_no IS NULL")
    ps = [s for s in select(db, "SELECT house_no, name, address, region_code, notice_date::text nd FROM presale WHERE region_code IS NOT NULL")]
    got = []
    for p in pcs:
        nk = _norm(p["apt_name"])
        exact = [s for s in ps if s["region_code"] == p["region_code"] and (_norm(s["name"]) in nk or nk in _norm(s["name"])) and _norm(s["name"])]
        if exact:
            got.append((p["pc_seq"], max(exact, key=lambda s: s["nd"] or "")["house_no"], "name"))
            continue
        dong = re.sub(r"\d+가$", "", (p["umd_name"] or "").split()[-1] if p["umd_name"] else "")
        best = None
        for s in ps:
            if s["region_code"][:2] != p["region_code"][:2] or (dong and dong[:-1] not in (s["address"] or "")):
                continue
            a, b = _norm(re.sub(r"\(.*?\)", "", p["apt_name"])), _norm(re.sub(r"\(.*?\)", "", s["name"]))
            if _nums(a) != _nums(b):
                continue
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if r >= 0.6 and (not best or r > best[0]):
                best = (r, s)
        if best:
            got.append((p["pc_seq"], best[1]["house_no"], f"fuzzy:{best[0]:.2f}"))
    if got:
        db.query("UPDATE presale_complexes p SET house_no = x.h, house_match = x.m FROM (VALUES "
                 + ", ".join(f"({lit(pc)}, {lit(h)}, {lit(m)})" for pc, h, m in got) + ") AS x (pc, h, m) WHERE p.pc_seq = x.pc;")
    return len(got)


def run(db: Db, regions: list[str], months: int, backfill: bool = False) -> int:
    yms = months_back(date.today(), months)
    total = 0
    try:
        for rc in regions:
            for ym in yms:
                rows = keyed(M.fetch_rights(rc, ym))
                if rows:
                    save(db, rows, backfill)
                    total += len(rows)
    except M.QuotaExceeded as e:
        print(f"  하루 한도: {e} → 여기까지 저장", file=sys.stderr)
    except M.ApiError as e:
        print(f"  멈춤: {e}", file=sys.stderr)
        link(db)
        return 2
    link(db)
    print(f"  분양 단지 ↔ 청약홈: 새로 {match_presale(db)}곳")
    s = select(db, "SELECT count(*) n, count(apt_seq) linked, count(*) FILTER (WHERE kind = '입주권') ip FROM right_deals")[0]
    print(f"  분양권·입주권: 이번 {total:,}건(시군구 {len(regions)} × {len(yms)}달), 전체 {s['n']:,}건 · 단지 연결 {s['linked']:,} · 입주권 {s['ip']:,}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--regions", help="쉼표로 시군구 코드. 기본 수도권 전체")
    ap.add_argument("--backfill", action="store_true", help="새로 넣는 행을 '새 거래'로 치지 않음(first_seen_date = 계약일)")
    a = ap.parse_args(argv)
    regions = a.regions.split(",") if a.regions else sorted(REGIONS)
    try:
        return run(connect(a.db), regions, a.months, a.backfill)
    except DbError as e:
        print(f"[right_deals] 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
