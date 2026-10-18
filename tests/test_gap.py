from datetime import date

from collector.gap import eligible, gap_stats, qkey, quarter_medians, quarters, targets


def test_quarters_and_key():
    qs = quarters(date(2026, 10, 18))
    assert qs[-1] == "2026Q3" and qs[0] == "2021Q4" and len(qs) == 20
    assert quarters(date(2026, 2, 1))[-1] == "2025Q4"
    assert qkey("202609") == "2026Q3" and qkey("202601") == "2026Q1"


def test_quarter_medians_filters():
    row = lambda p, area="84.9", fl="5", dt="중개", c="0", m="202608": {"apt_seq": "A", "contract_month": m, "area_m2": area, "floor": fl,
                                                                         "deal_type": dt, "is_cancelled": c, "price_10k": str(p)}
    rows = [row(100), row(120), row(999, fl="1"), row(999, dt="직거래"), row(999, c="1"), row(999, area="59.9"), row(999, m="201001")]
    assert quarter_medians(rows, quarters(date(2026, 10, 18))) == {"A": {"2026Q3": 110}}


def _s(qs, start, step):
    return {q: start + step * i for i, q in enumerate(qs)}


def test_gap_stats_and_targets():
    qs = quarters(date(2026, 10, 18))
    a = _s(qs, 50000, 1000)                       # 5억 → 6.9억
    b = {q: 120000 - 500 * i for i, q in enumerate(qs)}   # 격차가 계속 줄어드는 목표 → 지금이 가장 좁다
    c = {q: v * 2.0 for q, v in a.items()}         # 격차가 계속 넓어짐
    far = {q: v * 1.8 for q, v in a.items()}
    cheap = {q: v * 1.2 for q, v in a.items()}     # 1.5배 미만은 후보 아님
    st = gap_stats(a, b, qs)
    assert st["n_q"] == 20 and st["gap_pct"] == 5.0 and st["gap_now_10k"] == b[qs[-1]] - a[qs[-1]]
    assert gap_stats(a, {q: b[q] for q in qs[:-1]}, qs) is None   # 마지막 분기에 목표 값이 없으면 계산 안 함
    assert eligible(a, qs) and not eligible({q: 1 for q in qs[:11]}, qs)
    co = {"A": (37.5, 127.0), "B": (37.52, 127.0), "C": (37.5, 127.05), "F": (37.7, 127.0), "X": (37.5, 127.01)}
    out = [t for t in targets({"A": a, "B": b, "C": c, "F": far, "X": cheap}, co, qs) if t["apt_seq"] == "A"]
    assert [t["target_seq"] for t in out] == ["B", "C"]          # F 는 10km 밖(약 22km), X 는 1.2배
    assert out[0]["rank"] == 1 and out[0]["gap_pct"] < out[1]["gap_pct"]


def test_series_mixed_boundary():
    """보관 경계가 분기 중간(202411)이면 그 분기는 보관 파일 행 + DB 원본 행을 합쳐 중앙값을 낸다."""
    from collector.archive import encode
    from jobs import gap as jg
    cols = ("apt_seq", "contract_month", "area_m2", "floor", "deal_type", "is_cancelled", "price_10k")
    files = {f"deals_{m}.csv.gz": encode([{"apt_seq": "A", "contract_month": m, "area_m2": "84.9", "floor": "5", "deal_type": "중개",
                                           "is_cancelled": "0", "price_10k": "100"}], cols)
             for m in jg._months(quarters(date(2026, 10, 18))) if m < "202411"}

    class Store:
        def get(self, name):
            return files.get(name)

    class Db:
        def query(self, sql):
            if "min(contract_month)" in sql:
                return [{"m": "202411"}]
            if "contract_month IN" in sql:   # 걸친 분기의 DB 원본
                return [{"apt_seq": "A", "contract_month": "202411", "area_m2": 84.9, "floor": 5, "deal_type": "중개", "is_cancelled": "0", "price_10k": 300}]
            return [{"apt_seq": "A", "q": "2025Q1", "p": 500}]

    s = jg.series(Db(), Store(), quarters(date(2026, 10, 18)))
    assert s["A"]["2024Q4"] == 200           # 보관 202410 = 100 + DB 202411 = 300 → 중앙값 200
    assert s["A"]["2024Q3"] == 100 and s["A"]["2025Q1"] == 500
