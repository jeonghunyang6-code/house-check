from collector.regions import REGIONS
from collector.sources import kosis


def test_sgg_codes():
    assert kosis.sgg_codes("경기", "수원시", REGIONS) == ["41111", "41113", "41115", "41117"]
    assert kosis.sgg_codes("서울", "중구", REGIONS) == ["11140"]
    assert kosis.sgg_codes("인천", "영종구", REGIONS) == ["28155"]
    assert kosis.sgg_codes("경기", "광주시", REGIONS) == [c for c, n in REGIONS.items() if n == "경기 광주시"]
    assert kosis.sgg_codes("경기", "없는시", REGIONS) == []


def test_fetch_unsold_sgg(monkeypatch):
    def fake(params):
        done = params["tblId"] == "DT_MLTM_5328"
        if params["objL1"] not in ("13102871087A.0002", "13102871088A.0002"):
            return {"err": "30"}
        return [{"PRD_DE": "202608", "C2_NM": "계", "DT": "898" if not done else "674"},
                {"PRD_DE": "202608", "C2_NM": "강동구", "DT": "262"},
                {"PRD_DE": "202608", "C2_NM": "마포구", "DT": "215" if not done else "50"}]
    monkeypatch.setattr(kosis, "_call", fake)
    out = kosis.fetch_unsold_sgg("202608", "202608")
    assert [(o["name"], o["unsold"], o["unsold_done"]) for o in out] == [("강동구", 262, 262), ("마포구", 215, 50)]


def test_fetch_income(monkeypatch):
    # 2026-10-19 실제 응답 모양 (DT_133001N_4215, C1 = 'A0101' 시군구 / 'A01' 시도, C2 = B02 총급여)
    def fake(params):
        assert params["tblId"] == kosis.INCOME_TABLE and params["objL2"] == "B02"
        rows = []
        for c1, nm, n, amt in (("A01", "서울", 100, 5000), ("A0101", "강남구", 10, 852), ("A0203", "미추홀구(남구)", 20, 680),
                               ("A0313", "수원시", 30, 1452), ("A0401", "강릉시", 5, 186)):
            rows += [{"PRD_DE": "2023", "C1": c1, "C1_NM": nm, "ITM_ID": "T001", "DT": str(n)},
                     {"PRD_DE": "2023", "C1": c1, "C1_NM": nm, "ITM_ID": "T002", "DT": str(amt)}]
        return rows
    monkeypatch.setattr(kosis, "_call", fake)
    out = kosis.fetch_income("2023", "2023")
    assert [(o["sido"], o["name"], o["persons"], o["pay_mil"]) for o in out] == [
        ("경기", "수원시", 30, 1452), ("서울", "강남구", 10, 852), ("인천", "미추홀구", 20, 680)]
    assert kosis.sgg_codes("인천", "미추홀구", REGIONS) == ["28177"]
