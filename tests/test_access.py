from collector import access as ac


def _st(rows):
    return {n: {"name": n, "lat": la, "lng": lo, "lines": set(ls)} for n, la, lo, ls in rows}


def test_canon_and_parse():
    assert ac.canon_line(" 인천지하철 1호선") == "인천1호선" and ac.canon_line("1호선(경인선)") == "1호선" and ac.canon_line("신분당") == "신분당선"
    text = "철도운영기관명,선명,역명,역간거리\nx,5호선,가나역,0\nx,5호선,B,1\nx,5호선,B,1\nx,5호선(마천),C(부기),1\nx,9호선,D,0\n"
    assert ac.parse_line_file(text) == [("5호선", ["가나", "B", "C"]), ("9호선", ["D"])]


def test_build_graph_branch_boundary_and_join():
    # 본선 A-B-C-D(동쪽으로), 지선 E-F 가 파일에서 D 뒤에 붙음. E 는 B 근처에서 갈라짐
    st = _st([("A", 37.5, 127.00, ["5호선"]), ("B", 37.5, 127.01, ["5호선"]), ("C", 37.5, 127.02, ["5호선"]),
              ("D", 37.5, 127.03, ["5호선"]), ("E", 37.49, 127.01, ["5호선"]), ("F", 37.48, 127.01, ["5호선"])])
    g = ac.build_graph(st, [("5호선", ["A", "B", "C", "D", "E", "F"])])
    nb = {k: {o for o, _ in v} for k, v in g["5호선"].items()}
    assert nb["D"] == {"C"}
    st["B2"] = dict(st["B"], name="B2")         # 같은 자리 옛 이름 역이 있어도 A-B 는 이어진다
    g2 = ac.build_graph(st, [("5호선", ["A", "B", "C", "D"])])
    assert "B" in {o for o, _ in g2["5호선"]["A"]}                 # D → E 는 사이에 C·B 가 끼어 버림
    assert "B" in nb["E"] and "F" in nb["E"]   # 끊긴 E-F 조각은 가장 가까운 B 에 붙음
    t = dict(g["5호선"]["A"])["B"]          # 약 885m × 1.15 ÷ 32.8km/h
    assert abs(t - 885 * 1.15 / 1000 / 32.8 * 60) < 0.1


def test_access_transfers_and_seq():
    st = _st([("H", 37.50, 127.00, ["2호선", "신분당선"]), ("G", 37.50, 127.02, ["2호선"]), ("S", 37.45, 127.00, ["신분당선"]),
              ("T1", 37.30, 127.00, ["GTX-A"]), ("T2", 37.20, 127.00, ["GTX-A"])])
    g = ac.build_graph(st, [("2호선", ["H", "G"]), ("신분당선", ["S", "H"])])
    assert "GTX-A" not in g                        # GTX-A 는 SEQ 로만 잇는다(SEQ 역 이름이 없으면 연결 없음)
    r = ac.access(g, {"G"})
    assert r["H"][1] == 0 and r["S"][1] == 1      # S → H(신분당) → 환승 → G(2호선)
    assert abs(r["S"][0] - (r["H"][0] + ac.TRANSFER_MIN + dict(g["신분당선"]["S"])["H"])) < 1e-9


def test_seq_fixed_minutes():
    old = ac.SEQ
    try:
        ac.SEQ = {"GTX-A": [(("P", "Q", "R"), 30.0)]}
        st = _st([("P", 37.0, 127.0, ["GTX-A"]), ("Q", 37.1, 127.0, ["GTX-A"]), ("R", 37.3, 127.0, ["GTX-A"])])
        g = ac.build_graph(st, [])
        assert abs(dict(g["GTX-A"]["P"])["Q"] - 10.0) < 0.01 and abs(dict(g["GTX-A"]["Q"])["R"] - 20.0) < 0.01
    finally:
        ac.SEQ = old
