"""H4 호재 단계: 수도권 주요 철도 사업 (0046, jobs/policy.py 가 함께 적재). 손으로 관리한다.

📖 교통 호재는 중심업무지구(사대문·여의도·강남) 연결이 핵심, 어디서 타는지보다 어디서 내리는지 p.68~70, p.86~87
📖 지하철은 착공 후 들어가도 늦지 않다. 진짜 악재는 사업 취소(지연은 악재 아님) p.279~280, p.357~358
📖 도로·IC·쇼핑몰·병원 등은 아파트 호재가 아니다 p.74~75, p.277~278 → 여기엔 철도만 둔다

status: 계획(계획에만 있음·예타 전) / 확정(예타 통과·계획 승인) / 착공 / 개통 / 예타탈락(취소에 가까운 악재 신호)
단계·날짜는 2026-10-18 웹 검색 기사로 확인(source), 2026-11-10 사업마다 언론사 2곳 이상으로 다시 확인(more, collector/provenance.py). region_codes(지나는 시군구)는 노선 경로를 손으로 적은 것이라 확인 필요.
cbd: 이 노선으로 갈아타지 않고 내리는 업무지구 (사대문·여의도·강남). 없으면 빈 칸
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Project:
    name: str
    status: str
    status_date: date | None      # 그 단계가 된 날(개통일·착공일·승인일). 모르면 None
    outlook: str                  # 다음 단계 전망(기사 표현 그대로 요약)
    cbd: tuple[str, ...]
    region_codes: tuple[str, ...]
    source: str
    stations: tuple[str, ...] = ()   # 이 사업이 서는 역 중 이미 station 표에 좌표가 있는 역(기존·개통 역) 이름
    # 새로 생기는 역(가칭): (이름, 위도, 경도). 역 위치가 공개되지 않아 기사에 나온 지명(교차로·학교·광장)의 좌표로 대략 잡음(2026-10-26, 카카오 장소 검색).
    # 지도 표시용. H4 역세권(700m) 계산에는 쓰지 않는다
    new_stations: tuple[tuple[str, float, float], ...] = ()
    # 교차 확인(collector/provenance.py, 2026-11-10~): 다른 출처, 확인한 날. 그 전 사업은 2026-10-18 웹 검색 확인(출처 1곳)
    more: tuple[str, ...] = ()
    checked: date = date(2026, 10, 18)

    @property
    def sources(self) -> tuple[str, ...]:
        return (self.source, *self.more)


PROJECTS: tuple[Project, ...] = (
    Project("GTX-A 운정중앙~서울역·수서~동탄", "개통", date(2024, 12, 28), "운행 중", ("사대문", "강남"),
            ("41480", "41287", "41281", "11380", "11140", "11680", "41135", "41463", "41597"), "https://www.newspim.com/news/view/20260608000776",
            stations=('운정중앙', '킨텍스', '대곡', '연신내', '서울', '수서', '성남', '구성', '동탄'),
            more=("https://www.etoday.co.kr/news/view/2432820", "https://www.newsis.com/view/NISX20241227_0003012601"), checked=date(2026, 11, 10)),
    Project("GTX-A 서울역~수서(삼성역)", "착공", None, "삼성역 철근 누락으로 무정차 통과 2027 상반기 검토(약 1년 지연, 2026-11)",
            ("사대문", "강남"), ("11140", "11680"), "https://www.newspim.com/news/view/20260608000776",
            stations=('삼성',),
            more=("https://www.mt.co.kr/index.php/estate/2026/11/03/2026110310274951459", "https://www.hankyung.com/article/202611032921i"), checked=date(2026, 11, 10)),
    Project("GTX-B 인천대입구~마석", "착공", None, "개통 목표 2030", ("여의도", "사대문"),
            ("28185", "28200", "28237", "41192", "11530", "11560", "11170", "11140", "11230", "11260", "41360"), "https://v.daum.net/v/20250302060029026",
            stations=('인천대입구', '인천시청', '부평', '부천종합운동장', '신도림', '여의도', '용산', '서울', '청량리', '망우', '별내', '평내호평', '마석'),
            more=("https://www.newsis.com/view/NISX20250401_0003122490", "https://news.ifm.kr/news/articleView.html?idxno=393383"), checked=date(2026, 11, 10)),
    Project("GTX-C 덕정~수원", "착공", date(2026, 9, 15), "공사비 중재 뒤 공사 재개, 개통 목표 2031", ("강남",),
            ("41630", "41150", "11320", "11350", "11230", "11200", "11680", "11650", "41290", "41173", "41410", "41115", "41271"),
            "https://news.bizwatch.co.kr/article/real_estate/2026/09/14/0015",
            stations=('덕정', '의정부', '창동', '광운대', '청량리', '왕십리', '삼성', '양재', '과천', '인덕원', '금정', '수원', '상록수'),
            more=("https://www.sisajournal-e.com/news/articleView.html?idxno=423713", "https://www.dtoday.co.kr/news/articleView.html?idxno=763273"), checked=date(2026, 11, 10)),
    Project("신안산선 안산·시흥~여의도", "착공", None, "광명 붕괴사고로 늦어져 개통 목표 2028 하반기(당초 2026)", ("여의도",),
            ("11560", "11530", "11545", "41171", "41210", "41390", "41271", "41273"), "https://v.daum.net/v/t8umTEaeZj",
            stations=('여의도', '영등포', '신풍', '대림', '구로디지털단지', '독산', '석수', '광명', '시흥시청', '중앙'),
            more=("https://www.segye.com/newsView/20260415526687", "https://v.daum.net/v/20260414124515661", "https://www.mt.co.kr/estate/2026/10/08/2026100722544643761"), checked=date(2026, 11, 10)),
    Project("동북선 왕십리~상계", "착공", None, "개통 목표 2028-08(2026-07 → 2027-11 → 다시 연기, 서울시 고시 예정)", (),
            ("11200", "11230", "11290", "11305", "11350"), "https://m.news.nate.com/view/20260312n31514",
            stations=('왕십리', '고려대', '미아사거리', '하계', '상계'),
            more=("http://www.dailypop.kr/news/articleView.html?idxno=104123", "https://www.electimes.com/news/articleView.html?idxno=351826"), checked=date(2026, 11, 10)),
    Project("7호선 청라 연장", "착공", None, "인천시 계획 1단계 2027 · 2단계 2029 개통(공사 중단·전동차 납품 차질로 지연 보도)", ("강남",),
            ("28275",), "https://v.daum.net/v/20251226195401097",
            stations=('청라국제도시',),
            more=("https://www.incheon.go.kr/iurail/IU010301", "https://www.incheontoday.com/news/articleView.html?idxno=261474", "https://www.khan.co.kr/article/202606171538001"), checked=date(2026, 11, 10)),   # 석남~청라국제도시(공항철도) 10.7km(etoday 1776673). 중간 새 역 위치는 확인 못 함
    Project("9호선 4단계(중앙보훈병원~고덕강일)", "착공", date(2023, 1, 3), "개통 목표 2028", ("강남", "여의도"),
            ("11740",), "https://www.infostockdaily.co.kr/news/articleView.html?idxno=187292",
            # 서울시 '중앙보훈병원 → 길동생태공원 앞 교차로 → 한영외고 → 고덕역(5호선) → 고덕강일1지구'(mediahub.seoul.go.kr/archives/2006605)
            stations=('고덕',),
            new_stations=(('길동생태공원', 37.53821, 127.15243), ('한영외고', 37.54813, 127.15722), ('고덕강일1지구', 37.56080, 127.17095)),
            more=("https://news.bizwatch.co.kr/article/real_estate/2023/01/03/0008", "https://www.khan.co.kr/article/202301031100001"), checked=date(2026, 11, 10)),
    Project("위례신사선", "확정", date(2026, 3, 10), "재정사업 전환 뒤 신속예타 통과, 기본계획 용역 중(개통 목표 미발표)", ("강남",),
            ("11710", "41131", "41450", "11680"), "https://www.mt.co.kr/policy/2026/02/13/2026021308445848671",
            # '위례중앙광장 → 가락시장 → 학여울 → 삼성 → 청담 → 신사(3호선)', 11개 역(dailian.co.kr/news/view/1002940). 나머지 새 역 이름·위치는 확인 못 함
            stations=('가락시장', '학여울', '삼성', '청담', '신사'),
            new_stations=(('위례중앙광장', 37.47300, 127.14185),),
            more=("https://www.newspim.com/news/view/20260310001052", "https://www.newsis.com/view/NISX20260310_0003542416"), checked=date(2026, 11, 10)),
    # 2026-11-09 추가(사용자 질문: 골든센트로 9호선 연장): 고덕강일 → 신강일(943, 강동) → 신미사(944, 하남) → 왕숙·진접2, 정거장 8곳(서울 1·하남 1·남양주 6).
    # 944 위치 = '미사강변 4·7·8단지 사이 미사강변대로 교차로'(기사)인데 좌표를 잡을 도구가 없어 new_stations 비움(구산성지 쪽 주민이 위치 변경 요구 중)
    # 2026-11-10 이름·전망을 9호선 4단계와 같은 꼴로(사용자). 강동구·서울시 매체는 '9호선 4단계 추가연장', 일부 언론은 '5단계' → 기사 2곳(시정일보·서울&)이 쓴 쪽.
    # 착공: 2024 기본계획 2026 → 2025-07 경기도 계약 의뢰 때 '2027 상반기 착공, 2031 개통'(철도경제신문·기호일보, 2026-11-10 교차 확인)
    Project("9호선 4단계 추가연장(강동하남남양주선, 고덕강일~미사~진접2)", "확정", date(2024, 12, 24), "착공 목표 2027 상반기 · 개통 목표 2031",
            ("강남", "여의도"), ("11740", "41450", "41360"), "https://www.sijung.co.kr/news/articleView.html?idxno=405579",
            more=("https://www.seouland.com/arti/society/society_general/19684.html", "https://www.munhwa.com/article/11474788",
                  "https://www.redaily.co.kr/news/articleView.html?idxno=12924", "https://www.kihoilbo.co.kr/news/articleView.html?idxno=1152251"),
            checked=date(2026, 11, 10)),
    Project("서부선 새절~서울대입구", "계획", None, "민자 우선협상대상자 지위 취소(2026-04 착수 · 07 확정), 재공고 준비 중(안 되면 재정 전환)", ("여의도",),
            ("11380", "11410", "11440", "11560", "11590", "11620"), "https://www.fnnews.com/news/202610100050441724",
            stations=('새절', '신촌', '여의도', '노량진', '장승배기', '서울대입구'),
            more=("https://www.mt.co.kr/policy/2026/04/01/2026033116543861758", "https://www.ajunews.com/view/20260401145352010"), checked=date(2026, 11, 10)),
    Project("강북횡단선 목동~청량리", "계획", None, "2024 예타 탈락 → 2026-06 제3차 도시철도망 계획에 정거장 2개 줄여 재추진(국토부 승인·예타 남음)", (),
            ("11470", "11440", "11410", "11110", "11290", "11230"), "https://www.fnnews.com/news/202610100050441724",
            more=("https://www.sedaily.com/article/20054274", "https://www.munhwa.com/article/11594727"), checked=date(2026, 11, 10)),
    Project("신분당선 서북부 연장(용산~삼송)", "예타탈락", date(2023, 8, 23), "GTX-A·3호선과 겹쳐 예타 탈락(B/C 0.36), 서울시 대안 노선 검토", ("사대문",),
            ("11170", "11140", "11110", "11380", "41281"), "https://www.hankyung.com/article/2023082985881",
            more=("https://mobile.newsis.com/view/NISX20230823_0002423724", "https://m.go.seoul.co.kr/news/2023/08/22/20230822500138"), checked=date(2026, 11, 10)),
)

STATUS_ORDER = ("개통", "착공", "확정", "계획", "예타탈락")
RULE = {
    "개통": "이미 가격에 반영된 편",
    "착공": "📖 착공 뒤 들어가도 늦지 않다(p.279~280). 지연은 악재가 아니다",
    "확정": "착공 전이라 기대 단계. 📖 착공 전 기대만으로 사지 마라(p.279~280)",
    "계획": "계획만 있는 단계. 📖 착공 전 기대만으로 사지 마라(p.279~280)",
    "예타탈락": "📖 진짜 악재는 사업 취소(p.279~280, p.357~358). 재추진 여부 확인",
}


def projects_at(station: str) -> list[Project]:
    return [p for p in PROJECTS if station in p.stations]


def projects_for(region_code: str) -> list[Project]:
    """이 시군구를 지나는 사업, 단계 순(개통 → 착공 → 확정 → 계획 → 예타탈락)."""
    return sorted((p for p in PROJECTS if region_code in p.region_codes), key=lambda p: STATUS_ORDER.index(p.status))
