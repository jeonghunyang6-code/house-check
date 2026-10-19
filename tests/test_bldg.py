from collector.bldg import params, recap_row, title_row


def test_params():
    assert params("1168010600", "316") == {"sigunguCd": "11680", "bjdongCd": "10600", "platGbCd": "0", "bun": "0316", "ji": "0000"}
    assert params("1168010600", "12-3")["ji"] == "0003"
    assert params("1168010600", "산12") is None and params("11680", "1") is None and params("1168010600", "") is None


def test_recap_and_title_rows():
    # 2026-10-19 실제 응답(헬리오시티 총괄표제부, 은마는 대지면적·용적률 0)
    r = recap_row([{"platArea": 346570.4, "vlRat": 285.98, "vlRatEstmTotArea": 991121.07, "totArea": 1563379.68, "hhldCnt": 9510, "mainBldCnt": 93}])
    assert (r["src"], r["vl_rat_calc"], r["land_per_hh"], r["hhld"]) == ("recap", 286.0, 36.4, 9510)
    e = recap_row([{"platArea": 0, "vlRat": 0, "vlRatEstmTotArea": 488472.85, "totArea": 528772, "hhldCnt": 4424, "mainBldCnt": 31}])
    assert e["plat_area"] is None and e["vl_rat_calc"] is None and e["land_per_hh"] is None and e["estm_area"] == 488472.85
    assert recap_row([]) is None
    t = title_row([{"mainPurpsCdNm": "공동주택", "platArea": 5000, "vlRat": 0, "vlRatEstmTotArea": 6000, "totArea": 7000, "hhldCnt": 60},
                   {"mainPurpsCdNm": "공동주택", "platArea": 5000, "vlRat": 0, "vlRatEstmTotArea": 4000, "totArea": 5000, "hhldCnt": 40},
                   {"mainPurpsCdNm": "판매시설", "platArea": 9000, "vlRatEstmTotArea": 1000, "hhldCnt": 0}])
    assert (t["src"], t["plat_area"], t["vl_rat_calc"], t["hhld"], t["land_per_hh"], t["main_bld"]) == ("title", 5000, 200.0, 100, 50.0, 2)
    assert title_row([{"mainPurpsCdNm": "판매시설", "hhldCnt": 0}]) is None
