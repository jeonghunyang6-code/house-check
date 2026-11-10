"""신도시·신규 공공택지 (D7 상승 여력 '추가 공급 토지', 📖 p.218~219). 손으로 관리한다(2026-11-10 사용자 요청).

📖 공급 효과는 입주 때 나타난다(입주장 5~6개월 전세↓), 대기 수요에 따라 지역마다 반대 p.54~56 → 발표가 아니라 입주 목표를 같이 적는다.
호수는 기사(서로 다른 언론사 2곳 이상, collector/provenance.py 등급 C)·정부 발표. 기사마다 다르면 범위. 모르는 칸은 비운다.
단지와의 거리는 지구 좌표가 없어 같은 시군구로만 묶는다.
stage: 발표(후보지) / 지구지정 / 착공 / 입주(첫 입주 시작)

교차 확인(2026-11-10): 입주 일정은 청약홈 입주자모집공고 입주 예정 월(등급 A, presale_sql)로 계산해 화면에 쓰고, first_move_in(손 값)과 매주 대조한다.
  기사 일정이 공고와 달랐던 곳: 창릉 기사 2029-05 ↔ 공고 첫 입주 2027-12(S-6), 대장 '2029 준공' ↔ 공고 2027-11(A-5·6).
  광명시흥 호수: 2021 발표 7만 → 2024-12-30 지구계획 승인 6.7만.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from collector.regions import REGIONS


@dataclass(frozen=True)
class NewTown:
    name: str
    region_codes: tuple[str, ...]
    homes: str            # 호수(기사 표현, 예 '3.7만', '3.2~3.3만')
    stage: str
    plan: str             # 다음 일정·목표(기사 표현). 공고가 없을 때 화면에 씀
    group: str            # 3기 신도시 / 8·13 / 10·29
    source: str
    year: int | None = None          # 호수를 발표(승인)한 해
    ps_kw: str | None = None         # 청약홈 공고 이름·주소에서 이 지구를 찾는 말(정규식)
    first_move_in: str | None = None  # 손으로 확인한 첫 입주 예정 월 YYYY-MM. 공고 첫 입주와 다르면 주간 요약에 뜸
    more: tuple[str, ...] = ()        # 교차 확인한 다른 출처
    checked: date = date(2026, 11, 10)

    @property
    def sources(self) -> tuple[str, ...]:
        return (self.source, *self.more)


S_1029 = "https://www.etoday.co.kr/news/view/2641758"
S_1029B = "https://m.inews24.com/v/2020363"
S_0813 = "https://www.fnnews.com/news/202608130835063140"
S_0813B = "https://www.sedaily.com/article/20078926"
S_3RD_HH = "https://www.newsis.com/view/NISX20191013_0000796780"   # 왕숙·교산·계양 호수(2019 발표)
S_3RD_GB = "https://news.mtn.co.kr/news-detail/2020052509090614776"   # 창릉·대장 호수
S_3RD_IN = "https://www.etoday.co.kr/news/view/2565309"              # 계양 첫 입주 2026-12, 왕숙·교산 2028·창릉·대장 2029 준공
S_3RD_DL = "https://www.m-i.kr/news/articleView.html?idxno=2015501"  # 왕숙2 입주 2029-02, 교산 2029-06 로 늦춰짐
S_GMSH = "https://kbthink.com/main/real-estate/government-policy/molit-press/2024/molit-press-241230.html"   # 국토부 보도자료 옮김: 6.7만
S_GMSH_B = "https://kyeonggi.com/article/20250109580143"

NEWTOWNS: tuple[NewTown, ...] = (
    NewTown("인천계양", ("28245",), "1.7만", "착공", "첫 입주 2026-12(A2·A3블록 1,285가구)", "3기 신도시", S_3RD_IN, 2019,
            "인천계양|계양지구|계양신도시", "2026-12", (S_3RD_HH,)),
    NewTown("남양주왕숙", ("41360",), "6.6만", "착공", "2028 준공 목표, 왕숙2 입주 2029-02로 늦춰짐", "3기 신도시", S_3RD_DL, 2019,
            "왕숙", "2028-05", (S_3RD_HH, S_3RD_IN)),
    NewTown("하남교산", ("41450",), "3.2~3.3만", "착공", "입주 2027 → 2029-06으로 늦춰짐", "3기 신도시", S_3RD_DL, 2019,
            "교산", "2029-06", (S_3RD_HH, S_3RD_IN)),
    NewTown("고양창릉", ("41281",), "3.8만", "착공", "2029 준공 목표", "3기 신도시", S_3RD_IN, 2019, "창릉", "2027-12", (S_3RD_GB,)),
    NewTown("부천대장", ("41196",), "2만", "착공", "2029 준공 목표", "3기 신도시", S_3RD_IN, 2019, "대장", "2027-11", (S_3RD_GB,)),
    NewTown("광명시흥", ("41210", "41390"), "6.7만", "지구지정", "2024-12-30 지구계획 승인, 입주 일정 확인 못 함", "3기 신도시", S_GMSH, 2024,
            "광명시흥", None, (S_GMSH_B,)),
    NewTown("서울 강서 염창", ("11500",), "0.1만", "발표", "2029 착공 목표", "8·13", S_0813, 2026, more=(S_0813B,)),
    NewTown("남양주 도심(와부)", ("41360",), "2.17만", "발표", "2027 하반기 지구지정, 2030 상반기 착공 목표", "8·13", S_0813, 2026, more=(S_0813B,)),
    NewTown("경기광주 역세권2", ("41610",), "0.45만", "발표", "2030 착공 목표", "8·13", S_0813, 2026, more=(S_0813B,)),
    NewTown("김포아라", ("41570",), "3.7만", "발표", "2027 지구지정, 2029 착공, 2035 완료 목표", "10·29",
            "https://www.gukjenews.com/news/articleView.html?idxno=3739652", 2026, more=(S_1029,)),
    NewTown("구리건원", ("41310",), "1.46만", "발표", "2030 안 착공 목표", "10·29", S_1029, 2026, more=(S_1029B,)),
    NewTown("하남미사 K-컬처", ("41450",), "1.2만", "발표", "2030 안 착공 목표", "10·29", S_1029, 2026, more=(S_1029B,)),
    NewTown("하남감일2", ("41450",), "0.65만", "발표", "2030 안 착공 목표", "10·29", S_1029, 2026, more=(S_1029B,)),
    NewTown("고양대곡 지식융합 확장", ("41281",), "0.4만", "발표", "2030 안 착공 목표", "10·29", S_1029, 2026, more=(S_1029B,)),
    NewTown("의정부다락원", ("41150",), "0.26만", "발표", "2030 안 착공 목표", "10·29", S_1029, 2026, more=(S_1029B,)),
)


def _lit(x: str) -> str:
    return "'" + x.replace("'", "''") + "'"


def presale_sql() -> str | None:
    """청약홈 공고(presale)에서 지구별 [첫 입주 월, 마지막 입주 월, 공고 수, 세대 합]. 분양(본청약·블록) 공고만, 잔여·추가·임대 공고는 뺀다.
    지구 이름이 공고 이름이나 주소에 있고, 시군구 코드가 맞거나(코드가 비면 주소의 시 이름)."""
    q = []
    for t in NEWTOWNS:
        if not t.ps_kw:
            continue
        city = "|".join(sorted({REGIONS[c].split()[1].rstrip("시구군") for c in t.region_codes}))
        q.append(f"SELECT {_lit(t.name)} AS nt, min(move_in_ym) a, max(move_in_ym) b, count(*) n, sum(households) hh FROM presale "
                 f"WHERE (name ~ {_lit(t.ps_kw)} OR address ~ {_lit(t.ps_kw)}) "
                 f"AND (region_code IN ({','.join(_lit(c) for c in t.region_codes)}) OR (region_code IS NULL AND address ~ {_lit(city)})) "
                 "AND (name || ' ' || coalesce(address, '')) ~ '본청약|블록|BL|신도시|지구' AND name !~ '잔여|추가|행복주택|국민임대|장기전세|영구임대' "
                 "AND move_in_ym IS NOT NULL")
    return " UNION ALL ".join(q) or None


def presale_rows(rows: list[dict]) -> dict[str, list]:
    return {r["nt"]: [r["a"], r["b"], int(r["n"]), int(r["hh"] or 0)] for r in rows if int(r["n"] or 0)}


def mismatches(ps: dict[str, list]) -> list[str]:
    """손 값(first_move_in)과 공고 첫 입주가 다른 지구. ps = {지구: [첫 입주 YYYYMM, …]}."""
    out = []
    for t in NEWTOWNS:
        got = ps.get(t.name)
        if not got:
            continue
        g = f"{got[0][:4]}-{got[0][4:]}"
        if t.first_move_in != g:
            out.append(f"{t.name}: 손 값 {t.first_move_in or '없음'} ↔ 공고 첫 입주 {g}")
    return out
