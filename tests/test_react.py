from collector.react import add_months, react_rows, zone_summary


def test_add_months():
    assert add_months("202601", -1) == "202512" and add_months("202512", 1) == "202601" and add_months("202306", -7) == "202211"


def test_react_rows():
    # 2024-01 입주(생활권 Z1, 서울). Z1 기존 단지 5곳: 전세 100 → 95 (−5%). 시도 다른 생활권 2곳: 100 → 99 (−1%) → rel −4%p
    ev = [{"house_no": "H", "z": "Z1", "move_in_ym": "202401", "hh": 1000, "sd": "11"}]
    rents, cx = [], {}
    for i in range(7):
        a = f"A{i}"
        z, post = ("Z1", 95.0) if i < 5 else ("Z2", 99.0)
        cx[a] = (z, 2010)
        for m in ("202308", "202312"):
            rents.append((a, 84, m, 100.0, 1, "11"))
        for m in ("202401", "202405"):
            rents.append((a, 84, m, post, 1, "11"))
    cx["NEW"] = ("Z1", 2023)                          # 입주 2년 전 이후 준공 → 뺌
    rents += [("NEW", 84, m, 50.0, 5, "11") for m in ("202310", "202402")]
    rents += [("X", 84, m, 50.0, 5, "11") for m in ("202310", "202402")]   # 단지 표에 없음 → 뺌
    rents += [("A0", 84, "202407", 10.0, 9, "11"), ("A0", 84, "202306", 10.0, 9, "11")]   # 창 밖 달
    out = react_rows(ev, rents, cx)
    assert out == [{"house_no": "H", "lifezone_id": "Z1", "move_in_ym": "202401", "total_hh": 1000,
                    "zone_chg": -5.0, "base_chg": -1.0, "rel": -4.0, "n": 5}]
    assert react_rows(ev, [r for r in rents if r[0] != "A4"], cx) == []    # 생활권 쪽 4곳 < 5
    assert zone_summary(out + [dict(out[0], house_no="H2", rel=-0.115)]) == {"Z1": (-2.06, 2)}
