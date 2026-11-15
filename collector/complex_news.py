"""관심 단지 소식 (jobs/complex_news.py → complex_news 0085). 2026-11-15 사용자 요청: 관심 단지 뉴스를 정기적으로 모아 상세 탭 맨 아래 '단지 소식'(A안).

네이버 뉴스(NAVER API HUB) 제목·요약문만 쓴다(본문은 열지도 저장하지도 않음, 제목·링크·날짜·언론사만).
규칙만으로 거른다(AI 요약·판단 없음 → 매일 돌아도 Claude 사용량 없음):
  - 단지 이름(공백 없이)이 **제목**에 들어간 기사만(2026-11-15 사용자: 요약문에만 나온 시장 정리·순위 기사는 그 단지 소식이 아님).
    이름이 짧으면(🔧 4글자 이하) 동·구 이름도 제목이나 요약문에 함께 있어야
  - '래미안솔베뉴어린이집'처럼 이름 바로 뒤에 시설 이름이 붙은 것만 있으면 뺀다
  - 같은 보도자료를 여러 언론사가 실은 것은 한 줄로 묶는다(제목 글자쌍이 🔧 20% 넘게 겹치고 3일 안) → '외 n곳'
딱지: 리모델링·재건축·시공사·조합·이주·거래·전세·사고·생활(앞에서부터 최대 2개, 점수 아님)
"""

from __future__ import annotations

import re
from datetime import date

from collector.provenance import outlet

SHORT = 4          # 🔧 이 글자 수 이하 이름은 동·구 이름도 함께 있어야
SAME_TITLE = 0.2   # 🔧 같은 기사로 묶는 제목 글자쌍 겹침(같은 단지·3일 안이라 느슨하게, 2026-11-15 선사현대 심의 기사 17곳 → 한 줄)
SAME_DAYS = 3
FACILITY = r"(어린이집|유치원|경로당|정류장|버스정류소|상가|교회)"
# 단지 이름이 기사에 다르게 쓰이는 경우(손으로)
ALIASES = {"11740-3": ("명일GS", "명일지에스")}
TAGS = (
    ("리모델링", r"리모델링"),
    ("재건축", r"재건축|정비구역|안전진단|정비계획"),
    ("시공사", r"시공사|시공권|건설사\s?선정"),
    ("조합", r"조합|총회|분담금"),
    ("이주", r"이주|철거"),
    ("거래", r"신고가|급매|하락|상승|억\s?원에\s?거래|거래됐|팔려|떨어진|오른"),
    ("전세", r"전세|월세"),
    ("사고", r"화재|사고|붕괴|누수|하자|침수"),
    ("생활", r"어린이집|학교|통학|도로|통행로|공원|주차"),
)
PRESS = {
    "chosun.com": "조선일보", "joongang.co.kr": "중앙일보", "donga.com": "동아일보", "hani.co.kr": "한겨레", "khan.co.kr": "경향신문",
    "hankyung.com": "한국경제", "mk.co.kr": "매일경제", "sedaily.com": "서울경제", "mt.co.kr": "머니투데이", "edaily.co.kr": "이데일리",
    "yna.co.kr": "연합뉴스", "newsis.com": "뉴시스", "news1.kr": "뉴스1", "heraldcorp.com": "헤럴드경제", "asiae.co.kr": "아시아경제",
    "fnnews.com": "파이낸셜뉴스", "etoday.co.kr": "이투데이", "ajunews.com": "아주경제", "dailian.co.kr": "데일리안", "seoul.co.kr": "서울신문",
    "kmib.co.kr": "국민일보", "segye.com": "세계일보", "hankookilbo.com": "한국일보", "munhwa.com": "문화일보", "bizwatch.co.kr": "비즈워치",
    "mtn.co.kr": "MTN", "sbs.co.kr": "SBS", "kbs.co.kr": "KBS", "imbc.com": "MBC", "jtbc.co.kr": "JTBC", "ytn.co.kr": "YTN",
    "newspim.com": "뉴스핌", "businesspost.co.kr": "비즈니스포스트", "mediapen.com": "미디어펜", "sisajournal-e.com": "시사저널e",
    "g-enews.com": "글로벌이코노믹", "inews24.com": "아이뉴스24", "dt.co.kr": "디지털타임스", "etnews.com": "전자신문", "kyeonggi.com": "경기일보",
    "kihoilbo.co.kr": "기호일보", "kukinews.com": "쿠키뉴스", "nocutnews.co.kr": "노컷뉴스", "ohmynews.com": "오마이뉴스", "pressian.com": "프레시안",
    "wowtv.co.kr": "한국경제TV", "mbn.co.kr": "MBN", "tvchosun.com": "TV조선", "ichannela.com": "채널A", "biz.heraldcorp.com": "헤럴드경제",
    "nate.com": "네이트", "aunews.co.kr": "아유경제", "dailypop.kr": "데일리팝", "redaily.co.kr": "부동산경제", "sijung.co.kr": "시정일보",
    "seouland.com": "서울&", "gangdong.go.kr": "강동구청", "seoul.go.kr": "서울시", "molit.go.kr": "국토교통부", "korea.kr": "정책브리핑",
    "hankyungrealty.com": "한경부동산", "landtoday.co.kr": "랜드투데이", "housingherald.co.kr": "하우징헤럴드", "hapt.co.kr": "한국아파트신문",
    "sentv.co.kr": "서울경제TV", "fntimes.com": "한국금융신문", "skyedaily.com": "스카이데일리", "areyou.co.kr": "아유경제",
    "bizhankook.com": "비즈한국", "gukjenews.com": "국제뉴스", "eroun.net": "이로운넷", "metroseoul.co.kr": "메트로신문", "ebn.co.kr": "EBN",
    "econovill.com": "이코노믹리뷰", "ekn.kr": "에너지경제", "cnbnews.com": "CNB뉴스", "thebell.co.kr": "더벨", "newsway.co.kr": "뉴스웨이", "newdaily.co.kr": "뉴데일리", "daily.hankooki.com": "데일리한국", "joseilbo.com": "조세일보",
}


def press_name(url: str) -> str:
    o = outlet(url)
    return PRESS.get(o) or o.split(".")[0]   # 모르는 언론사는 주소 앞부분(newswhoplus.com → newswhoplus)


def core_name(name: str) -> str:
    """'선사현대아파트' → '선사현대', '위례24단지(꿈에그린)' → '위례24단지', '미사강변 골든 센트로' → '미사강변골든센트로'."""
    n = re.sub(r"\(.*?\)", "", name or "")
    n = re.sub(r"\s+", "", n)
    n = re.sub(r"(아파트|APT)$", "", n)
    return n


def names_of(seq: str, apt_name: str) -> tuple[str, ...]:
    out = [core_name(apt_name)] + list(ALIASES.get(seq, ()))
    return tuple(dict.fromkeys(x for x in out if len(x) >= 2))


def matches(text: str, names: tuple[str, ...], places: tuple[str, ...]) -> bool:
    t = re.sub(r"\s+", "", text or "")
    for n in names:
        hits = [m.end() for m in re.finditer(re.escape(n), t)]
        if not hits or all(re.match(FACILITY, t[e:]) for e in hits):
            continue
        if len(n) <= SHORT and not any(p and p in t for p in places):
            continue
        return True
    return False


def in_title(title: str, names: tuple[str, ...]) -> bool:
    """제목에 단지 이름(시설 이름 붙은 것 빼고). 동·구 이름은 요약문까지 보고 이미 맞춘 뒤라 여기선 안 봄"""
    t = re.sub(r"\s+", "", title or "")
    return any(any(not re.match(FACILITY, t[m.end():]) for m in re.finditer(re.escape(n), t)) for n in names)


def tags_of(text: str) -> list[str]:
    return [k for k, rx in TAGS if re.search(rx, text or "")][:2]


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"[\s\[\]【】<>‘’'\"“”…·,.!?~()]+", "", s or "")
    return {s[i:i + 2] for i in range(len(s) - 1)}


def same_story(a: str, b: str) -> bool:
    x, y = _bigrams(a), _bigrams(b)
    return bool(x and y) and len(x & y) / len(x | y) >= SAME_TITLE


def group(rows: list[dict]) -> list[dict]:
    """rows: {title, url, outlet, pub(date), in_title, tags} 최신순 아니어도 됨 → 묶음 [{…대표, 'others': n}] 최신순.
    대표 = 제목에 단지 이름이 있는 것 우선, 그다음 먼저 나온 기사."""
    rs = sorted(rows, key=lambda r: (r["pub"], r["url"]))
    groups: list[list[dict]] = []
    for r in rs:
        for g in groups:
            if abs((r["pub"] - g[0]["pub"]).days) <= SAME_DAYS and any(same_story(r["title"], x["title"]) for x in g):
                g.append(r)
                break
        else:
            groups.append([r])
    out = []
    for g in groups:
        head = sorted(g, key=lambda r: (not r["in_title"], r["pub"]))[0]
        tags = list(dict.fromkeys(t for r in g for t in (r.get("tags") or [])))[:2]
        out.append({**head, "tags": tags, "others": len({r["outlet"] for r in g}) - 1, "last": max(r["pub"] for r in g)})
    return sorted(out, key=lambda r: (r["last"], r["pub"]), reverse=True)


def cutoff(today: date, days: int = 183) -> date:
    from datetime import timedelta
    return today - timedelta(days=days)
