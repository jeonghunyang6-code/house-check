from datetime import date, timedelta

from collector.market import b4, breadth, monthly, phase, run_length


def _months(vals):
    return [(f"{2025 + (i // 12)}{i % 12 + 1:02d}", v) for i, v in enumerate(vals)]


def test_monthly_takes_last_week_of_month():
    pts = [(date(2026, 9, 7), 100.0), (date(2026, 9, 28), 101.0), (date(2026, 10, 5), 102.0)]
    assert monthly(pts) == [("202609", 101.0), ("202610", 102.0)]


def test_phase_labels():
    up = phase(_months([100 + i for i in range(13)]))               # 12개월 +12%, 12개월 상승
    assert up.phase == "상승장" and up.up_months == 12 and up.last3 == "상승" and up.drawdown == 0
    down = phase(_months([100 - i for i in range(13)]))
    assert down.phase == "하락장" and round(down.drawdown, 2) == round(12 / 100 * 100 / 1, 2)
    flat = phase(_months([100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 101.5]))
    assert flat.phase == "보합장"
    # 12개월 +5% 이지만 상승한 달이 5개뿐, 최근 3개월 연속 상승 → 일시 반등
    bounce = phase(_months([100, 99, 98, 97, 96, 95, 94, 93, 92, 95, 99, 102, 105]))
    assert bounce.phase == "일시 반등" and bounce.up_months == 4
    assert phase(_months([100] * 5)).phase is None                  # 13개월 미만


def test_breadth_counts_leaves_only():
    prev = {"서울": 100, "서울>강남지역": 100, "서울>강남지역>동남권>강남구": 100, "서울>강남지역>동남권": 100,
            "서울>강북지역>도심권>종로구": 100, "인천>제물포구": 100, "세종": 100, "수도권": 100, "4대광역시": 100}
    cur = dict(prev, **{"서울>강남지역>동남권>강남구": 99, "서울>강북지역>도심권>종로구": 101, "서울": 100.5, "세종": 100.2, "수도권": 99})
    n, up, down = breadth(cur, prev)
    assert (n, up, down) == (4, 2, 1)   # 강남구·종로구·제물포구·세종 (상위 지역과 묶음 집계는 제외)


def test_run_length_and_b4():
    assert run_length([5, 4, 3, 4, 3, 2, 1], -1) == 3 and run_length([1, 2, 3], +1) == 2 and run_length([1, 1], +1) == 0
    assert b4(75.0, 9, None) == (2, 2, "대세 하락 의심")
    assert b4(40.0, 9, None) == (1, 2, "단기 조정")
    assert b4(None, None, None) == (0, 0, "단기 조정")


def test_new_jeonse():
    from collector.market import new_jeonse
    cnt = {f"2025{m:02d}": (100, 50) for m in range(1, 13)} | {f"2026{m:02d}": (80, 70) for m in range(1, 13)}
    nj = new_jeonse(cnt, "202608", 1.2)
    assert nj.months == ("202606", "202607", "202608") and (nj.n_new, nj.n_new_prev, nj.yoy) == (240, 300, -20.0)
    assert nj.renew_share == 46.7 and nj.state == "충족"
    assert new_jeonse(cnt, "202608", -0.5).state == "미충족"
    assert new_jeonse(cnt, "202508", 1.0).state == "데이터 없음"   # 1년 전 자료 없음


def test_b5_state():
    from collector.market import b5_state
    assert b5_state(None, None) == "데이터 없음"
    assert b5_state(3.0, 0.1) == "보통"
    assert b5_state(9.9, 0.3) == "보통"
    assert b5_state(10.0, 0.3) == "주의"
    assert b5_state(30.0, 0.5) == "주의"      # 비중은 높아도 상위가 더 많이 오르면 과열 아님
    assert b5_state(25.0, 0.6) == "과열"
    assert b5_state(30.0, None) == "주의"


def test_rebound_state_only_when_falling():
    from collector.market import rebound_state
    up4 = [90, 91, 92, 93, 94]
    assert rebound_state(up4, [100 + i for i in range(20)]) == (4, "하락 중 아님")
    falling = [120 - i for i in range(20)]
    assert rebound_state(up4, falling) == (4, "상승 전환")
    assert rebound_state([90, 91, 92, 91.5, 92], falling) == (1, "아님")
    assert rebound_state(up4, [100, 99]) == (4, "하락 중 아님")   # 13주 비교 불가


def test_b4_applies():
    from collector.market import Phase, b4_applies
    assert not b4_applies(None)
    assert b4_applies(Phase(-5, 2, 9, "하락", "하락장", 6))
    assert b4_applies(Phase(2.9, 4, 8, "하락", "보합장", 1.4))   # 2022-08~11 수도권
    assert not b4_applies(Phase(6.8, 12, 0, "상승", "상승장", 0))
