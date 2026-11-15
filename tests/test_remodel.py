from datetime import date

from collector import remodel as R
from collector.provenance import grade


def test_title_stage():
    dg = R.idx("도계위")
    assert R.title_stage("망우동 상생주택·선사현대 리모델링 서울시 심의 통과", dg) == R.idx("건축심의")   # 어떤 심의인지 없으면 다음 심의 단계
    assert R.title_stage("망우동 상생주택·선사현대 리모델링 서울시 심의 통과", -1) == R.idx("도계위")
    assert R.title_stage("선사현대 리모델링 건축심의 앞두고 기대감", dg) is None                         # 안 끝난 말
    assert R.title_stage("선사현대 사업계획승인 신청", dg) is None
    assert R.title_stage("선사현대 리모델링, 사업계획승인 받아…이주 2029년 목표", dg) == R.idx("사업승인")  # 마디별로 봄
    assert R.title_stage("선사현대, 리모델링으로 3206가구 탈바꿈", dg) is None
    assert R.title_stage("성내삼성 리모델링 조합설립인가", -1) == R.idx("조합설립")
    assert R.title_stage("롯데·현대, 선사현대 리모델링 시공사 선정", -1) == R.idx("시공사")


def test_detect_needs_three_press_and_moves_forward_only():
    r = lambda t, o, d: {"title": t, "outlet": o, "url": o, "pub": d}
    rows = [r("선사현대 리모델링 서울시 심의 통과", "뉴시스", date(2026, 11, 11)),
            r("선사현대아파트 리모델링 서울시 심의 통과", "뉴스핌", date(2026, 11, 11)),
            r("서울시, 선사현대 리모델링 심의 통과", "thepowernews", date(2026, 11, 12))]
    got = R.detect(rows, R.idx("도계위"))
    assert [g["stage"] for g in got] == ["건축심의"] and len(got[0]["press"]) == 3 and got[0]["first"] == date(2026, 11, 11)
    assert R.detect(rows[:2], R.idx("도계위")) == []                 # 2곳이면 아직
    assert R.detect(rows, R.idx("건축심의")) == []                    # 이미 지난 단계는 안 올림
    far = rows[:2] + [r("서울시, 선사현대 리모델링 심의 통과", "x", date(2026, 11, 20))]
    assert R.detect(far, R.idx("도계위")) == []                       # 3일 넘게 떨어지면 따로


def test_hand_steps_cross_checked_and_ordered():
    for seq, m in R.REMODELS.items():
        idxs = [R.idx(s.stage) for s in m.steps]
        assert idxs == sorted(idxs), seq
        for s in m.steps:
            assert grade(s.sources) in ("B", "C"), (seq, s.stage)   # 손 관리 사실: 발표 또는 언론사 2곳 이상
            assert len(s.d) in (7, 10) and s.note
