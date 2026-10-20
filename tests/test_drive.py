import io
import json
import urllib.error

from collector import drive as V


def test_parse():
    # 공식 문서 응답 모양: route.trafast[0].summary.duration(ms)·distance(m)
    d = {"code": 0, "message": "길찾기를 성공하였습니다.", "route": {"trafast": [{"summary": {"duration": 3_000_000, "distance": 51_234}}]}}
    assert V.parse(d) == (50.0, 51.2)
    assert V.parse({"code": 1, "message": "출발지와 도착지가 동일합니다."}) is None
    assert V.parse({"code": 0, "route": {}}) is None


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_call_and_stop():
    seen = []

    def ok(req, timeout=0):
        seen.append(req)
        return _Resp(json.dumps({"code": 0, "route": {"trafast": [{"summary": {"duration": 60000, "distance": 1000}}]}}).encode())
    d = V.call(37.5, 127.0, "skh_icheon", "id", "k", V.URLS[0], opener=ok)
    assert V.parse(d) == (1.0, 1.0)
    u = seen[0].full_url
    assert "start=127.0%2C37.5" in u and "goal=127.48069%2C37.25298" in u and "option=trafast" in u
    assert seen[0].get_header("X-ncp-apigw-api-key-id") == "id"

    def denied(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "x", {}, io.BytesIO(b"{}"))
    try:
        V.call(37.5, 127.0, "skh_icheon", "id", "k", V.URLS[0], opener=denied)
        assert False
    except V.Stop:
        pass
    # 첫 주소가 401 이면 둘째 주소
    calls = []

    def second_only(req, timeout=0):
        calls.append(req.full_url)
        if req.full_url.startswith(V.URLS[0]):
            raise urllib.error.HTTPError(req.full_url, 401, "x", {}, io.BytesIO(b"{}"))
        return ok(req)
    assert V.pick_base(37.5, 127.0, "id", "k", opener=second_only) == V.URLS[1]
