"""sql/metrics.sql 통합 테스트. HC_TEST_PG_URL(빈 로컬 DB) 이 있을 때만 돈다."""
import os
from datetime import date
from pathlib import Path

from collector.db import PsqlDb, lit, select
from jobs.metrics import render

ROOT = Path(__file__).parent.parent
URL = os.environ.get("HC_TEST_PG_URL")
TODAY = date(2026, 10, 12)


def _db():
    db = PsqlDb(URL)
    db.query("DROP TABLE IF EXISTS deal_events, deals, rent_events, rents, snapshot_runs, rent_monthly, archive_cells, complex_metrics, "
             "macro_monthly, deal_anchor, deal_region_month, region_phase, market_signals, rone_weekly, rone_regions, complexes, kapt_complexes, "
             "adm_dong, adm_adjacent, lifezone, presale, ipju_plan, rent_j24 CASCADE;")
    for m in ("0001_deals.sql", "0005_snapshot_runs.sql", "0006_rents.sql", "0007_rent_archive.sql", "0010_metrics.sql",
              "0009_rone_weekly.sql", "0011_market.sql", "0012_macro.sql", "0013_macro_annual.sql", "0014_complex_phase.sql", "0015_quadrant_strength.sql",
              "0016_reverse_real.sql", "0008_complexes.sql", "0019_deal_anchor.sql", "0020_turnover_e3.sql",
              "0022_complex_geo.sql", "0023_adm_dong.sql", "0030_lifezone.sql", "0031_e2.sql", "0032_e4_e5_e7.sql", "0034_presale.sql", "0035_presale_total.sql", "0037_ipju_plan.sql",
              "0039_rent_j24.sql"):
        db.query((ROOT / "db" / "migrations" / m).read_text(encoding="utf-8"))
    return db


def _deal(db, seq, d, price, dtype="중개", cancelled=False, n=[0], area=84.9, floor=5):
    n[0] += 1
    db.query("INSERT INTO deals (deal_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, floor, "
             "price_10k, deal_type, is_cancelled, last_seen_date) VALUES "
             f"({lit(f'k{n[0]}')}, {lit(seq)}, 'x', '11680', {lit(d.replace('-', '')[:6])}, {lit(date.fromisoformat(d))}, {area}, {floor}, "
             f"{price}, {lit(dtype)}, {lit(cancelled)}, {lit(TODAY)});")


def test_metrics_end_to_end():
    if not URL:
        return
    db = _db()
    # A: 2021 전고점 15억, 2023 저점 10억, 최근 60일 16·17·18억 → 기준 17억, 신고가 돌파
    for d in ("2021-06-05", "2021-06-20", "2021-07-10"):
        _deal(db, "A", d, 150000)
    _deal(db, "A", "2023-01-15", 100000)
    _deal(db, "A", "2026-09-01", 160000); _deal(db, "A", "2026-09-10", 170000); _deal(db, "A", "2026-10-01", 180000)
    _deal(db, "A", "2026-10-02", 999999, dtype="직거래")             # 직거래는 무시
    _deal(db, "A", "2026-10-03", 990000, cancelled=True)            # 해제도 무시
    _deal(db, "A", "2026-10-04", 100000, floor=1)                    # 1층은 기준 시세에서 빼고 거래 수에는 넣는다
    db.query("INSERT INTO rent_monthly VALUES ('A', 84, '202610', '11680', 'x', 3, 81000, 2, 90000, 1, 0, NULL, NULL, 0, 0);")
    # 전세 기준은 rent_monthly 가 아니라 원본 rents 의 실제 중앙값: 신규 79,000·81,000 → 80,000 (갱신·월세·사라짐 제외)
    for i, (dep, rent, typ, gone) in enumerate([(79000, 0, '신규', False), (81000, 0, '신규', False), (95000, 0, '갱신', False),
                                                (30000, 100, '신규', False), (10000, 0, '신규', True)]):
        db.query("INSERT INTO rents (rent_key, apt_seq, apt_name, region_code, contract_month, contract_date, area_m2, "
                 "deposit_10k, monthly_rent_10k, contract_type, used_renewal_right, last_seen_date, disappeared) "
                 f"VALUES ('r{i}', 'A', 'x', '11680', '202610', '2026-10-0{i + 1}', 84.9, {dep}, {rent}, '{typ}', FALSE, "
                 f"'2026-10-10', {gone});")
    # D3 2년 전 전세: A 는 보관 파일 실제 중앙값(rent_j24) 85,000(3건), 근사(rent_monthly) 70,000 보다 우선. C 는 근사만
    db.query("INSERT INTO rent_j24 VALUES ('A', 84, '202409', '202411', 3, 85000), ('A', 59, '202312', '202402', 5, 1);")
    db.query("INSERT INTO rent_monthly VALUES ('A', 84, '202410', '11680', 'x', 4, 70000, 0, NULL, 4, 0, NULL, NULL, 0, 0), "
             "('C', 84, '202410', '11680', 'x', 2, 60000, 0, NULL, 2, 0, NULL, NULL, 0, 0);")
    # B: 최근 거래 2건뿐 → 기준 시세 없음
    _deal(db, "B", "2026-10-01", 50000); _deal(db, "B", "2026-10-05", 51000)
    # C: 최근 60·90일엔 없고 100~180일 전 3건 → 180일 창, 신뢰도 낮음. 전고점 20억, 저점 10억, 현재 14억 → 회복 40% 지연
    _deal(db, "C", "2021-09-01", 200000); _deal(db, "C", "2023-03-01", 100000)
    for d in ("2026-05-01", "2026-05-10", "2026-06-01"):
        _deal(db, "C", d, 140000)

    db.query(render(TODAY, 4000))
    m = {r["apt_seq"]: r for r in select(db, "SELECT * FROM complex_metrics")}
    a, b, c = m["A"], m["B"], m["C"]
    assert (a["ref_10k"], a["ref_n"], a["ref_days"], a["confidence"]) == (170000, 3, 60, "높음")
    assert (a["peak_10k"], a["peak_month"], a["trough_10k"], a["pattern"]) == (150000, "202106", 100000, "신고가 돌파")
    assert (a["jeonse_10k"], a["jeonse_n"], a["jeonse_src"], float(a["jeonse_ratio"])) == (80000, 2, "신규", 47.1)
    assert (float(a["band_lo"]), float(a["band_hi"])) == (42.0, 56.0)       # 17억: 50→30, 60→50 구간 40% 지점
    assert a["high_10k"] == 180000 and a["n_365"] == 4
    assert b["ref_10k"] is None and b["pattern"] is None and b["jeonse_ratio"] is None
    assert (c["ref_10k"], c["ref_days"], c["confidence"], c["pattern"], float(c["recovery"])) == (140000, 180, "낮음", "회복 지연", 0.4)
    assert c["no_rebound"] is False
    assert (a["jeonse_24m_10k"], a["jeonse_24m_n"], a["reverse_risk"], a["jeonse_24m_approx"]) == (85000, 3, True, False)
    assert (c["jeonse_24m_10k"], c["jeonse_24m_n"], c["jeonse_24m_approx"]) == (60000, 2, True)
    # 전고점: 18억 거래 직전 최고가는 17억 (직거래 999,999 와 해제 990,000 은 제외)
    ph = {r["price_10k"]: r["prev_high_10k"] for r in select(db, "SELECT price_10k, prev_high_10k FROM deals WHERE apt_seq = 'A'")}
    assert ph[180000] == 170000 and ph[160000] == 150000 and ph[150000] in (None, 150000)


def test_metrics_with_deal_anchor():
    """저장 구조 C: 2년 전 거래는 DB 에 없고 deal_anchor 에 고정값만 있다."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO deal_anchor VALUES ('D', 84, 200000, '2021-08-01', 190000, '202108', 120000, '202212', 90000);")
    _deal(db, "D", "2026-09-01", 150000); _deal(db, "D", "2026-09-10", 160000); _deal(db, "D", "2026-10-01", 170000)
    db.query(render(TODAY, 4000))
    d = select(db, "SELECT * FROM complex_metrics WHERE apt_seq = 'D'")[0]
    assert (d["ref_10k"], d["peak_10k"], d["peak_month"], d["trough_10k"], d["trough_month"]) == (160000, 190000, "202108", 120000, "202212")
    assert d["pattern"] == "회복 지연" and float(d["recovery"]) == 0.571
    assert d["high_10k"] == 200000 and str(d["high_date"]) == "2021-08-01" and d["base2020_10k"] == 90000
    prev = {r["price_10k"]: r["prev_high_10k"] for r in select(db, "SELECT price_10k, prev_high_10k FROM deals WHERE apt_seq = 'D'")}
    assert prev == {150000: 200000, 160000: 200000, 170000: 200000}   # 보관 구간 최고가가 전고점


def test_metrics_turnover_e3():
    """C2 회전율(세대수 대비 월 거래), E3 같은 시군구에서 ㎡당 10~40% 비싼 단지."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO kapt_complexes (kapt_code, kapt_name, region_code, households, listed_at) VALUES ('KA', 'a', '11680', 200, '2026-10-01'), ('KB', 'b', '11680', 1000, '2026-10-01');")
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, kapt_code, updated_at) VALUES "
             "('A', 'a', '11680', '역삼동', 'KA', '2026-10-01'), ('B', 'b', '11680', '역삼동', 'KB', '2026-10-01'), "
             "('C', 'c', '11680', '대치동', NULL, '2026-10-01');")
    # A: 2025-09~2026-08 에 12건(해제 1건 빼고) → 월 1건 / 200세대 = 0.5% → 꽤 괜찮음. 기준 시세 10억
    for mth in range(9, 21):
        y, mm = 2025 + (mth - 1) // 12, (mth - 1) % 12 + 1
        _deal(db, "A", f"{y}-{mm:02d}-10", 100000)
    _deal(db, "A", "2026-08-11", 100000, cancelled=True)
    for d in ("2026-09-01", "2026-09-10", "2026-10-01"):
        _deal(db, "A", d, 100000)
        _deal(db, "B", d, 120000)      # B: ㎡당 20% 비쌈 → A 의 E3
        _deal(db, "C", d, 200000)      # C: 100% 비쌈 → 제외
    db.query(render(TODAY, 4000))
    m = {r["apt_seq"]: r for r in select(db, "SELECT * FROM complex_metrics")}
    a = m["A"]
    assert (a["households"], float(a["turnover_pct"]), a["turnover_state"]) == (200, 0.5, "꽤 괜찮음")
    assert m["B"]["turnover_state"] == "적음" and m["C"]["turnover_pct"] is None
    assert (a["e3_seqs"], a["e3_target_10k"]) == ("B", 120000)
    assert m["B"]["e3_seqs"] is None          # C 는 B 보다 67% 비싸 범위 밖


def test_metrics_e3_lifezone():
    """E3: 같은 생활권 먼저, 아니면 5km 안·한강 같은 쪽 가까운 순. 한강 건너는 가까워도 뺀다."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO adm_dong (adm_cd, adm_nm, year, han_side) VALUES ('S1', 's', 2025, '남'), ('N1', 'n', 2025, '북');")
    rows = [("A", 37.5000, 127.0000, "Z1", "S1"), ("F", 37.5000, 127.0700, "Z1", "S1"),   # F: 약 6.2km 지만 같은 생활권
            ("P1", 37.5050, 127.0000, "Z2", "S1"), ("P2", 37.5100, 127.0000, "Z2", "S1"),   # 0.6km·1.1km, 다른 생활권
            ("R", 37.5020, 127.0000, "Z3", "N1"),                                              # 0.2km 지만 한강 건너
            ("P3", 37.5000, 127.0300, "Z2", "S1")]                                             # 2.6km
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at, lat, lng, lifezone_id, adm_cd) VALUES " + ", ".join(
        f"({lit(s)}, 'x', '11680', '역삼동', '2026-10-01', {la}, {lo}, {lit(z)}, {lit(ad)})" for s, la, lo, z, ad in rows) + ";")
    for d in ("2026-09-01", "2026-09-10", "2026-10-01"):
        _deal(db, "A", d, 100000)
        for s in ("F", "P1", "P2", "R", "P3"):
            _deal(db, s, d, 120000)
    db.query(render(TODAY, 4000))
    a = {r["apt_seq"]: r for r in select(db, "SELECT * FROM complex_metrics")}["A"]
    assert a["e3_seqs"] == "F,P1,P2"          # 같은 생활권 F 먼저, 그다음 가까운 P1·P2 (R 은 한강 건너, P3 는 4번째)


def test_metrics_e2():
    """E2: 같은 생활권 다른 단지 ㎡당 기준 시세 중앙값 대비. 3곳 안 되면 1.5km 안(한강 같은 쪽)."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO adm_dong (adm_cd, adm_nm, year, han_side) VALUES ('S1', 's', 2025, '남'), ('N1', 'n', 2025, '북');")
    rows = [("A", 37.5000, 127.0000, "Z1", "S1", 100000), ("B", 37.5000, 127.0300, "Z1", "S1", 120000),
            ("C", 37.5000, 127.0350, "Z1", "S1", 140000), ("D", 37.5000, 127.0400, "Z1", "S1", 130000),
            ("X", 37.6000, 127.0000, "Z9", "S1", 100000), ("Y", 37.6050, 127.0000, "Z8", "S1", 150000),
            ("W", 37.6080, 127.0000, "Z7", "S1", 150000), ("V", 37.6100, 127.0000, "Z6", "S1", 150000),
            ("R", 37.6020, 127.0000, "Z5", "N1", 300000)]
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at, lat, lng, lifezone_id, adm_cd) VALUES " + ", ".join(
        f"({lit(s)}, 'x', '11680', '역삼동', '2026-10-01', {la}, {lo}, {lit(z)}, {lit(ad)})" for s, la, lo, z, ad, _ in rows) + ";")
    for d in ("2026-09-01", "2026-09-10", "2026-10-01"):
        for s, *_, p in rows:
            _deal(db, s, d, p)
    db.query(render(TODAY, 4000))
    m = {r["apt_seq"]: r for r in select(db, "SELECT * FROM complex_metrics")}
    assert (float(m["A"]["e2_ratio"]), m["A"]["e2_n"], m["A"]["e2_basis"]) == (0.769, 3, "생활권")     # 10억 ÷ 13억
    assert (float(m["X"]["e2_ratio"]), m["X"]["e2_n"], m["X"]["e2_basis"]) == (0.667, 3, "반경 1.5km")  # R 은 한강 건너


def test_metrics_e4():
    """E4 ① 84㎡ 천장 = E3 비교 단지 59㎡ 기준 시세, ② 단지 안 평형 압축 (작가 예 24평 11억 / 32평 13억 / 42평 14억)."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at) VALUES "
             "('A', 'a', '11680', '역삼동', '2026-10-01'), ('B', 'b', '11680', '역삼동', '2026-10-01');")
    for d in ("2026-09-01", "2026-09-10", "2026-10-01"):
        _deal(db, "A", d, 110000, area=59.9)
        _deal(db, "A", d, 130000, area=84.9)
        _deal(db, "A", d, 140000, area=114.9)
        _deal(db, "B", d, 156000, area=84.9)        # ㎡당 20% 비쌈 → A 84 의 E3
        _deal(db, "B", d, 125000, area=59.9)        # B 59㎡ 12.5억 = A 84㎡ 천장
    db.query(render(TODAY, 4000))
    m = {(r["apt_seq"], r["area_group"]): r for r in select(db, "SELECT * FROM complex_metrics")}
    a = m[("A", 84)]
    assert a["e3_seqs"] == "B" and (a["e4_cap_10k"], a["e4_cap_n"]) == (125000, 1)
    assert m[("A", 59)]["e4_cap_10k"] is None                     # 84㎡ 행만
    assert float(a["e4_compress"]) == 0.417 and float(m[("A", 114)]["e4_compress"]) == 0.417   # (1억/30㎡) ÷ (2억/25㎡)
    assert a["e4_sizes"] == "59㎡ 11.0억 / 84㎡ 13.0억 / 114㎡ 14.0억"
    assert m[("B", 84)]["e4_compress"] is None                    # 대형 거래 없음


def test_metrics_e5_e7():
    """E5 생활권 대형/중형 ㎡당 비율(단지 3곳+), E7 신축·준신축·구축 ㎡당 중앙가(구간 단지 2곳+)."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO lifezone (zone_id, name, units, n_complex, built) VALUES ('Z1', 'z', 'S:a', 5, '2026-10-01');")
    cx = [("N1", 2023, 120000), ("N2", 2022, 100000), ("M1", 2015, 90000), ("M2", 2012, 80000), ("O1", 2000, 60000)]
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at, build_year, lifezone_id) VALUES " + ", ".join(
        f"({lit(s)}, 'x', '11680', '역삼동', '2026-10-01', {y}, 'Z1')" for s, y, _ in cx) + ";")
    for d in ("2026-09-01", "2026-10-01"):
        for i, (s, _, p) in enumerate(cx):
            _deal(db, s, d, p, area=84.0)
            if i < 3:
                _deal(db, s, d, round(p * 120 / 84 * (0.8 + 0.05 * i)), area=120.0)   # ㎡당 비율 0.80 / 0.85 / 0.90
    db.query(render(TODAY, 4000))
    z = select(db, "SELECT * FROM lifezone")[0]
    assert (float(z["e5_ratio"]), z["e5_n"]) == (0.85, 3)
    # 신축 N1·N2: 84㎡ 와 120㎡ 섞인 단지 중앙가 → 두 단지 중앙값. 구축은 1곳이라 없음
    assert z["e7_n"] == "2/2/1" and z["e7_old_ppm"] is None
    assert float(z["e7_mid_ppm"]) == round((90000 * (1 + 0.9) / 2 / 84 + 80000 / 84) / 2, 1)
    assert z["e7_new_ppm"] is not None


def test_metrics_f1():
    """F1: 같은 생활권·시군구 24개월 입주 공급 세대, 입주장(최근 6개월 입주), 가장 큰 다음 입주."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at, lifezone_id) VALUES "
             "('A', 'a', '11680', '역삼동', '2026-10-01', 'Z1'), ('B', 'b', '11680', '역삼동', '2026-10-01', 'Z2');")
    for d in ("2026-09-01", "2026-10-01"):
        _deal(db, "A", d, 100000)
        _deal(db, "B", d, 100000)
    rows = [("p1", "입주중", 500, "202606", "Z1"), ("p2", "다음", 800, "202703", "Z1"), ("p3", "작은", 100, "202612", "Z1"),
            ("p4", "멀리", 900, "202901", "Z1"), ("p5", "옛날", 700, "202601", "Z1"), ("p6", "옆생활권", 300, "202701", "Z2")]
    db.query("INSERT INTO presale (house_no, name, address, households, move_in_ym, region_code, lifezone_id, updated) VALUES " + ", ".join(
        f"({lit(h)}, {lit(n)}, 'x', {hh}, {lit(ym)}, '11680', {lit(z)}, '2026-10-12')" for h, n, hh, ym, z in rows) + ";")
    db.query("UPDATE presale SET total_hh = 1600 WHERE house_no = 'p2';")   # 정비사업 총 세대 보정이 있으면 그 값을 쓴다
    db.query(render(TODAY, 4000))
    a = select(db, "SELECT * FROM complex_metrics WHERE apt_seq = 'A'")[0]
    assert (a["f1_zone_24m"], a["f1_sgg_24m"]) == (1700, 2000)          # 2026-10 ~ 2028-09: 다음 800 + 작은 100 (+ 옆생활권 300 은 시군구만)
    assert a["f1_ipju"] == "입주중(2026.06, 500세대)"                  # 2026-05 ~ 2026-10 입주
    assert a["f1_next"] == "다음(2027.03, 1600세대)"


def test_metrics_f1_plan():
    """한국부동산원 입주 예정 물량이 다루는 달(2026-07~2027-06)은 그 표만, 범위 밖 달은 청약홈."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at, lifezone_id) VALUES ('A', 'a', '11680', '역삼동', '2026-10-01', 'Z1');")
    for d in ("2026-09-01", "2026-10-01"):
        _deal(db, "A", d, 100000)
    db.query("INSERT INTO presale (house_no, name, address, households, move_in_ym, region_code, lifezone_id, updated, total_hh) VALUES "
             "('p1', '청약홈안', 'x', 100, '202703', '11680', 'Z1', '2026-10-12', 230), "      # 부동산원 범위 안 → 무시
             "('p2', '청약홈밖', 'x', 300, '202801', '11680', 'Z1', '2026-10-12', NULL);")    # 범위 밖 → 사용
    db.query("INSERT INTO ipju_plan (name, address, area, kind, households, move_in_ym, region_code, lifezone_id, file_name, loaded) VALUES "
             "('부동산원', 'x', '서울', '분양임대', 3064, '202703', '11680', 'Z1', 'f', '2026-10-12'), "
             "('지난입주', 'x', '서울', '분양', 500, '202607', '11680', 'Z1', 'f', '2026-10-12'), "
             "('끝', 'x', '서울', '임대', 10, '202706', '11680', 'Z2', 'f', '2026-10-12');")
    db.query(render(TODAY, 4000))
    a = select(db, "SELECT * FROM complex_metrics WHERE apt_seq = 'A'")[0]
    assert (a["f1_zone_24m"], a["f1_sgg_24m"]) == (3364, 3374)
    assert a["f1_ipju"] == "지난입주(2026.07, 500세대)" and a["f1_next"] == "부동산원(2027.03, 3064세대)"


def test_metrics_prev_high_after_cancel():
    """오래된 거래가 나중에 해제되면, 전고점 재계산 기간(PREV_DAYS) 밖 거래도 그 단지·면적군은 다시 계산한다."""
    if not URL:
        return
    db = _db()
    db.query("INSERT INTO complexes (apt_seq, apt_name, region_code, umd_name, updated_at) VALUES ('A', 'a', '11680', '역삼동', '2026-10-01');")
    _deal(db, "A", "2026-01-10", 150000)            # 나중에 해제될 고가
    _deal(db, "A", "2026-03-10", 120000)
    _deal(db, "A", "2026-05-10", 125000)            # PREV_DAYS(30) 밖
    db.query(render(TODAY, 4000))
    pick = lambda: {r["contract_date"].isoformat() if hasattr(r["contract_date"], "isoformat") else r["contract_date"]: r["prev_high_10k"]
                    for r in select(db, "SELECT contract_date::text AS contract_date, prev_high_10k FROM deals")}
    assert pick()["2026-05-10"] == 150000
    key = select(db, "SELECT deal_key FROM deals WHERE price_10k = 150000")[0]["deal_key"]
    db.query(f"UPDATE deals SET is_cancelled = true WHERE deal_key = {lit(key)}; "
             f"INSERT INTO deal_events (deal_key, event, event_date) VALUES ({lit(key)}, 'cancelled', {lit(TODAY)});")
    db.query(render(TODAY, 30))
    assert pick()["2026-05-10"] == 120000             # 해제된 15억이 빠지고 3월 12억
