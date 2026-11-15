import io
import json
import urllib.error

import pytest

from collector.projects import PROJECTS
from jobs import policy
from jobs.redev_geo import Stop
from jobs.station_geo import addrs, geocode


class _R(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_geocode_parses_and_stops():
    body = {"addresses": [{"x": "127.1912345", "y": "37.5654321", "roadAddress": "경기도 하남시 미사강변대로 240"}]}
    assert geocode("q", "k", "s", opener=lambda req, timeout: _R(json.dumps(body).encode())) == (37.56543, 127.19123, "경기도 하남시 미사강변대로 240")
    assert geocode("q", "k", "s", opener=lambda req, timeout: _R(b'{"addresses": []}')) is None

    def denied(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "x", {}, io.BytesIO(b'{"error":"Permission Denied"}'))
    with pytest.raises(Stop):
        geocode("q", "k", "s", opener=denied)


def test_policy_merges_found_stations_only():
    a = addrs()
    assert a and all(x.startswith(("서울", "경기", "인천")) for x in a)
    sql = policy.statements({a[0]: (37.5, 127.2)})
    nm = next(n for p in PROJECTS for n, x in p.geo_stations if x == a[0])
    assert json.dumps([nm, 37.5, 127.2], ensure_ascii=False) in sql
    assert json.dumps([nm, 37.5, 127.2], ensure_ascii=False) not in policy.statements({})
