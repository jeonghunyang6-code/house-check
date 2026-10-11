from collector.sources.auction_news import Candidate, confirm, extract

# 실제 보도(파이낸셜뉴스 2026-10-07, 검색 결과에 인용된 문장)의 일부
REAL = "서울 아파트 낙찰가율은 94.7%로 집계됐다. 지난해 2월 91.8%를 기록한 이후 1년 7개월 만에 가장 낮은 수준이다."
# 아래는 구조를 흉내 낸 예시 문장 (실제 기사 전문으로 검증한 것이 아님)
SYNTH = (
    "전국 아파트 낙찰가율은 85.9%로 전월(84.7%) 대비 1.2%p 상승했다. "
    "이 가운데 낙찰가율 상승폭이 큰 지역은 울산이었다. 제주는 75.5%로 전월(82.5%)보다 7.0%p 떨어졌다."
)


def test_real_sentence_only_seoul_not_91_8():
    out = extract(REAL)
    assert [(c.region, c.ratio_pct) for c in out] == [("서울", 94.7)]


def test_pattern1_with_prev():
    out = {c.region: c for c in extract(SYNTH)}
    assert out["전국"].ratio_pct == 85.9
    assert out["전국"].prev_pct == 84.7


def test_pattern2_needs_nakchalgayul_context():
    assert any(c.region == "제주" and c.ratio_pct == 75.5 for c in extract(SYNTH))
    # '낙찰가율' 언급이 없는 기사에서는 같은 모양이어도 뽑지 않는다 (예: 낙찰률·응찰자 수 문장 오인 방지)
    assert extract("제주는 75.5%로 전월(82.5%)보다 7.0%p 떨어져 하락했다.") == []


def test_unrelated_percentages_ignored():
    assert extract("지난해 2월 91.8%를 기록한 이후 1년 7개월 만에 가장 낮은 수준이다.") == []


def test_confirm_requires_two_distinct_articles():
    a = [Candidate("서울", 94.7, None, "")]
    b = [Candidate("서울", 94.7, None, ""), Candidate("경기", 89.0, None, "")]
    assert confirm({"A": a, "B": b}) == {"서울": 94.7}  # 경기는 1건뿐이라 제외


def test_confirm_same_article_twice_counts_once():
    a = [Candidate("서울", 94.7, None, ""), Candidate("서울", 94.7, None, "")]
    assert confirm({"A": a}) == {}


def test_confirm_conflicting_values_not_confirmed():
    arts = {
        "A": [Candidate("서울", 94.7, None, "")], "B": [Candidate("서울", 94.7, None, "")],
        "C": [Candidate("서울", 93.9, None, "")], "D": [Candidate("서울", 93.9, None, "")],
    }
    assert confirm(arts) == {}
