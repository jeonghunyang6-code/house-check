from datetime import date, timedelta

from collector.liquidity import Info, Window, decline_window, liquidity, months_between, region_windows, shift, window_for


def weekly(points: list[tuple[date, float]], start=date(2020, 1, 6), end=date(2023, 12, 25)):
    """points 사이를 직선으로 잇는 주간 시계열."""
    out, d = [], start
    while d <= end:
        for (a, va), (b, vb) in zip(points, points[1:]):
            if a <= d <= b:
                out.append((d, va + (vb - va) * (d - a).days / max((b - a).days, 1)))
                break
        d += timedelta(days=7)
    return out


def test_month_helpers():
    assert months_between("202201", "202304") == 15
    assert shift("202201", -1) == "202112" and shift("202212", 1) == "202301" and shift("202001", -12) == "201901"


def test_decline_window():
    s = weekly([(date(2020, 1, 6), 80), (date(2022, 1, 17), 100), (date(2023, 5, 15), 85), (date(2023, 12, 25), 90)])
    w = decline_window(s)
    assert (w.peak_m, w.trough_m, w.source) == ("202201", "202305", "sgg")
    assert -15.5 < w.drop_pct < -14.5
    # 2021-01 전부터 이어지지 않는 시계열(신설 구)은 판정하지 않는다
    assert decline_window([x for x in s if x[0] >= date(2022, 3, 1)]) is None


def test_region_windows_sido_fallback():
    s = weekly([(date(2020, 1, 6), 80), (date(2022, 1, 17), 100), (date(2023, 5, 15), 85), (date(2023, 12, 25), 90)])
    ws = region_windows({"28": s, "28140": [x for x in s if x[0] >= date(2022, 3, 1)]})
    assert "28140" not in ws and ws["28"].source == "sido"
    assert window_for(ws, "28140") is ws["28"] and window_for(ws, "11680") is None


def _row(seq, m, deal_type="중개", cancelled="0"):
    return {"apt_seq": seq, "contract_month": m, "deal_type": deal_type, "is_cancelled": cancelled}


def test_liquidity_counts_ranks_and_exclusions():
    w = Window("202112", "202312", -15.0, "sgg")   # 상승 24개월, 하락 24개월
    ws = {"11000": w}
    info = {f"s{i}": Info("11000", 1000, date(2010, 1, 1)) for i in range(5)}
    info["new"] = Info("11000", 1000, date(2019, 6, 1))     # 고점 36개월 전보다 늦게 입주 → 뺀다
    info["mid"] = Info("11000", 1000, date(2018, 6, 1))     # C3 는 되지만 2020-01 의 36개월 안 입주라 C4 없음
    info["other"] = Info("41000", 500, None)                # 구간 없는 지역 → 뺀다
    rows = []
    for i in range(5):
        rows += [_row(f"s{i}", "202106")] * 24             # 상승 구간 월 1건
        rows += [_row(f"s{i}", "202301")] * (i * 6)        # 하락 구간 0, 6, 12, 18, 24 건
    rows += [_row("s4", "202301", "직거래")] * 50 + [_row("s4", "202301", cancelled="1")] * 50   # 직거래·해제는 세지 않는다
    rows += [_row("s1", "202401")] * 99                    # 저점 뒤는 세지 않는다
    rows += [_row("mid", "202301")] * 12
    out = {o["apt_seq"]: o for o in liquidity(iter(rows), ws, info)}
    assert set(out) == {"s0", "s1", "s2", "s3", "s4", "mid"}
    s0, s4 = out["s0"], out["s4"]
    assert s0["down_n"] == 0 and s0["down_turnover"] == 0 and s0["down_rank"] == 0 and s0["keep_ratio"] == 0
    assert s4["down_n"] == 24 and s4["down_turnover"] == 0.1 and s4["down_rank"] == 100   # 24건 ÷ 24개월 ÷ 1000세대
    assert s4["up_turnover"] == 0.1 and s4["keep_ratio"] == 1.0 and s4["keep_rank"] == 100
    assert out["s1"]["down_n"] == 6
    assert out["mid"]["up_n"] is None and out["mid"]["keep_ratio"] is None and out["mid"]["keep_rank"] is None
    assert out["mid"]["down_rank"] is not None             # 하락 구간 분위에는 들어간다 (6곳)


def test_rank_needs_min_region():
    ws = {"11000": Window("202112", "202312", -15.0, "sgg")}
    info = {f"s{i}": Info("11000", 100, None) for i in range(4)}
    out = liquidity(iter([]), ws, info)
    assert len(out) == 4 and all(o["down_rank"] is None for o in out)
