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
