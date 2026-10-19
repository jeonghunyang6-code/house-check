from collector.locality import centroids, e8_rows


def test_e8_rows():
    cx = [
        {"apt_seq": "a", "region_code": "1", "umd_name": "상", "lat": 37.50, "lng": 127.00},   # 1급지
        {"apt_seq": "b", "region_code": "1", "umd_name": "상", "lat": 37.52, "lng": 127.00},
        {"apt_seq": "c", "region_code": "2", "umd_name": "중", "lat": 37.55, "lng": 127.00},   # 4급지
        {"apt_seq": "d", "region_code": "3", "umd_name": "하", "lat": 37.60, "lng": 127.00},   # 6급지
        {"apt_seq": "e", "region_code": "4", "umd_name": "무", "lat": 37.70, "lng": 127.00},   # 급지 없음
        {"apt_seq": "f", "region_code": "4", "umd_name": "무", "lat": None, "lng": None},
    ]
    cents = centroids(cx)
    assert abs(cents[("1", "상")][0] - 37.51) < 1e-9 and ("4", "무") in cents
    out = {r["apt_seq"]: r for r in e8_rows(cx, {("1", "상"): 1, ("2", "중"): 4, ("3", "하"): 6}, cents)}
    assert "f" not in out
    assert out["a"]["up_m"] is None and out["a"]["top_m"] is None                       # 1급지: 위도 최상급지도 없음
    assert (out["c"]["up_dong"], out["c"]["up_grade"]) == ("상", 1) and abs(out["c"]["up_m"] - 4453) < 5
    assert out["c"]["top_dong"] == "상" and out["c"]["top_m"] == out["c"]["up_m"]
    assert (out["d"]["up_dong"], out["d"]["up_grade"]) == ("중", 4)                     # 가장 가까운 위 급지(4급지)
    assert out["d"]["top_dong"] == "상"
    assert out["e"]["grade"] is None and out["e"]["up_m"] is None and out["e"]["top_dong"] == "상"
