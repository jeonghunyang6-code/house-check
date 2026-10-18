"""지역 월별 지표 적재 (region_monthly, 0045) + 홈 신호 (market_signals: d1_region_jeonse, g7_sentiment). rone.yml 이 매주 돌린다.

    python -m jobs.region_stats            # 전세가율·소비심리(R-ONE) + 연령별 인구(KOSIS)
    python -m jobs.region_stats --only rone|pop

R-ONE: 처음엔 지역마다 전체 시계열(2012~), 그다음부터는 최근 3개월만 달 단위로 다시 받는다.
KOSIS 인구: 시군구 83곳 + 시도 3곳, 처음엔 2011-12 부터, 그다음은 최근 3개월. 해마다 12월 + 최근 25개월만 남긴다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from collector.db import Db, DbError, connect, lit, select
from collector.region_stats import jeonse_state, pop_keep, sentiment_state, ym_add
from collector.regions import REGIONS
from collector.sources import kosis
from collector.sources.molit import ApiError, QuotaExceeded
from collector.sources.rone import JEONSE_RATIO_TABLE, SENTIMENT_TABLE, fetch_monthly, map_regions, region_key

KST = ZoneInfo("Asia/Seoul")
RONE = {"jeonse_ratio": (JEONSE_RATIO_TABLE, "201201"), "sentiment": (SENTIMENT_TABLE, "201201")}
POP_START = "201112"
REVISE = 3


def upsert(db: Db, rows: list[tuple[str, str, str, float]]) -> None:
    for i in range(0, len(rows), 2000):
        db.query("INSERT INTO region_monthly (series, region, period, value) VALUES "
                 + ", ".join(f"({lit(s)}, {lit(r)}, {lit(p)}, {lit(float(v))})" for s, r, p, v in rows[i:i + 2000])
                 + " ON CONFLICT (series, region, period) DO UPDATE SET value = EXCLUDED.value;")


def _keyed(rows: list[dict]) -> list[tuple[str, int, str]]:
    """R-ONE 행 → [(region key, cls_id, full name)] 수도권·전국만."""
    names = sorted({r["CLS_FULLNM"] for r in rows if r.get("CLS_FULLNM")})
    sgg = map_regions(names, REGIONS)
    out = []
    for r in rows:
        k = region_key(r.get("CLS_FULLNM") or "", sgg)
        if k:
            out.append((k, int(r["CLS_ID"]), r["CLS_FULLNM"]))
    return out


def run_rone(db: Db, today: date) -> int:
    rc = 0
    last_month = ym_add(today.strftime("%Y%m"), -1)
    for series, (tbl, start) in RONE.items():
        have = select(db, f"SELECT max(period) AS p FROM region_monthly WHERE series = {lit(series)}")[0]["p"]
        try:
            if not have:   # 처음: 최근 발표 달의 지역 목록 → 지역마다 전체 시계열
                cur = []
                for k in range(0, 4):
                    cur = fetch_monthly(tbl, ym=ym_add(last_month, -k))
                    if cur:
                        break
                rows = []
                for key, cls, _ in {(k, c, n) for k, c, n in _keyed(cur)}:
                    rows += [(series, key, r["WRTTIME_IDTFR_ID"], float(r["DTA_VAL"])) for r in fetch_monthly(tbl, cls_id=cls)
                             if r.get("DTA_VAL") is not None and r["WRTTIME_IDTFR_ID"] >= start]
            else:
                rows, ym = [], ym_add(have, -REVISE)
                while ym <= last_month:
                    got = fetch_monthly(tbl, ym=ym)
                    keys = {c: k for k, c, _ in _keyed(got)}
                    rows += [(series, keys[int(r["CLS_ID"])], ym, float(r["DTA_VAL"])) for r in got
                             if int(r["CLS_ID"]) in keys and r.get("DTA_VAL") is not None]
                    ym = ym_add(ym, 1)
        except (ApiError, QuotaExceeded) as e:
            print(f"  {series}: 실패 {e}", file=sys.stderr)
            rc = 1
            continue
        rows = list({(s, k, p): (s, k, p, v) for s, k, p, v in rows}.values())
        if rows:
            upsert(db, rows)
        print(f"  {series}: {len(rows)}행, 지역 {len({r[1] for r in rows})}곳" + (f", 최신 {max(r[2] for r in rows)}" if rows else ""), flush=True)
    return rc


def run_pop(db: Db, today: date) -> int:
    have = select(db, "SELECT max(period) AS p FROM region_monthly WHERE series = 'pop_total'")[0]["p"]
    start, end = (ym_add(have, -REVISE) if have else POP_START), today.strftime("%Y%m")
    rc, rows, latest = 0, [], have or start
    for code in [*REGIONS, "11", "28", "41"]:
        try:
            got = kosis.fetch_population(code, start, end)
        except (ApiError, QuotaExceeded) as e:
            print(f"  인구 {code}: 실패 {e}", file=sys.stderr)
            rc = 1
            continue
        for p, g in got.items():
            latest = max(latest, p)
            rows += [(f"pop_{k}", code, p, v) for k, v in g.items()]
    rows = [r for r in rows if pop_keep(r[2], latest)]
    if rows:
        upsert(db, rows)
    db.query(f"DELETE FROM region_monthly WHERE series LIKE 'pop_%' AND period NOT LIKE '%12' AND period <= {lit(ym_add(latest, -25))};")
    print(f"  인구: {len(rows)}행, 최신 {latest}", flush=True)
    return rc


def signals(db: Db, today: date) -> None:
    def last(series: str, region: str) -> list[dict]:
        return select(db, f"SELECT period, value FROM region_monthly WHERE series = {lit(series)} AND region = {lit(region)} "
                          "ORDER BY period DESC LIMIT 13")
    sig = {}
    js, jc = last("jeonse_ratio", "11"), last("jeonse_ratio", "SUDO")
    if js:
        v = float(js[0]["value"])
        sgg = select(db, f"""SELECT count(*) FILTER (WHERE value < 50) AS lo, count(*) FILTER (WHERE value >= 80) AS hi, count(*) AS n
            FROM region_monthly WHERE series = 'jeonse_ratio' AND length(region) = 5 AND period = {lit(js[0]['period'])}""")[0]
        sig["d1_region_jeonse"] = (round(v, 1), jeonse_state(v),
            f"{js[0]['period'][:4]}.{js[0]['period'][4:]} 서울 아파트 중위 전세가율 {v:.1f}%"
            + (f"(1년 전 {float(js[12]['value']):.1f}%)" if len(js) > 12 else "")
            + (f", 수도권 {float(jc[0]['value']):.1f}%" if jc else "")
            + f". 수도권 시군구 {sgg['n']}곳 중 50% 미만 {sgg['lo']}곳·80% 이상 {sgg['hi']}곳. ▶ 시장 평균 60% 균형, 50% 이하면 투자 수요 유입 어려움, 80~90% 조심 (한국부동산원 표본 중위값)")
    ss, sc = last("sentiment", "11"), last("sentiment", "SUDO")
    if ss:
        v = float(ss[0]["value"])
        sig["g7_sentiment"] = (round(v, 1), sentiment_state(v),
            f"{ss[0]['period'][:4]}.{ss[0]['period'][4:]} 서울 부동산시장 소비심리지수 {v:.1f}"
            + (f"(3개월 전 {float(ss[3]['value']):.1f})" if len(ss) > 3 else "")
            + (f", 수도권 {float(sc[0]['value']):.1f}" if sc else "")
            + ". 국토연구원 기준 95 미만 하강·95~115 보합·115 이상 상승. 📖 심리는 객관성에 한계가 있어 보조로만(p.51~52)")
    if sig:
        db.query("INSERT INTO market_signals (key, asof, value, state, detail) VALUES "
                 + ", ".join("(" + ", ".join(lit(x) for x in (k, today, *t)) + ")" for k, t in sig.items())
                 + " ON CONFLICT (key) DO UPDATE SET asof = EXCLUDED.asof, value = EXCLUDED.value, state = EXCLUDED.state, detail = EXCLUDED.detail;")
        for k, t in sig.items():
            print(f"  신호 {k}: {t[1]} — {t[2]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["api", "psql"])
    ap.add_argument("--only", choices=["rone", "pop"])
    a = ap.parse_args(argv)
    today = datetime.now(KST).date()
    try:
        db = connect(a.db)
        rc = 0
        if a.only in (None, "rone"):
            rc |= run_rone(db, today)
        if a.only in (None, "pop"):
            rc |= run_pop(db, today)
        signals(db, today)
    except DbError as e:
        print(f"[region_stats] 실패: {e}", file=sys.stderr)
        return 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
