from collector.grade import Complex, dong_grades, grade_of, is_small, wquantile


def test_grade_of_cuts():
    assert grade_of(48.1) == 1 and grade_of(30) == 1 and grade_of(29.9) == 2
    assert grade_of(25) == 2 and grade_of(15) == 4 and grade_of(14.99) == 5
    assert grade_of(12) == 5 and grade_of(9) == 6 and grade_of(6) == 7 and grade_of(5.9) == 8


def test_is_small():
    c = lambda hh, n: Complex("11", "가동", "x", 2000, 1, n, hh)
    assert is_small(c(299, 50)) and not is_small(c(300, 1))
    assert is_small(c(None, 19)) and not is_small(c(None, 20))   # K-apt 미연결: 거래 수로 추정


def test_wquantile():
    assert wquantile([(10, 1), (20, 1), (30, 1)], 0.5) == 20
    assert wquantile([(10, 3), (20, 1)], 0.5) == 10


def test_dong_grades_small_weight_and_flags():
    cs = [Complex("11740", "둔촌동", "올림픽파크포레온", 2024, 277000, 62, 12032),
          Complex("11740", "둔촌동", "둔촌푸르지오", 2010, 164000, 55, 800),
          Complex("11740", "둔촌동", "소단지A", 1990, 100000, 40, 150),
          Complex("11740", "둔촌동", "소단지B", 1988, 105000, 40, 160),
          Complex("11110", "가동", "a", 2000, 50000, 5, 500), Complex("11110", "가동", "b", 2000, 60000, 5, 500)]
    out = dong_grades(cs, 2026)
    assert len(out) == 1                       # 단지 3개 미만 동은 뺀다
    g = out[0]
    # 소단지 80건이 0.3 가중(24) → 대단지 117건 쪽 중앙값
    assert g["value_10k"] == 164000 and g["grade"] == 4
    assert g["new_big_name"] == "올림픽파크포레온" and g["new_big_10k"] == 277000
    assert not g["flag_rebuild"] and g["old_share"] == round(80 / 197, 3)
