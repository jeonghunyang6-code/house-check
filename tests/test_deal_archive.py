import tempfile

import jobs.deal_archive as da
from collector.archive import LocalDirStore, decode


class _Db:
    def query(self, sql):
        assert "ORDER BY" not in sql            # 디스크가 꽉 찼을 때 정렬 임시 파일을 피한다
        m = sql.split("contract_month = '")[1][:6]
        base = {c: None for c in da.DEAL_COLUMNS}
        return [base | {"deal_key": f"k{i}", "region_code": "11680", "contract_month": m, "is_cancelled": False,
                        "price_10k": 100 + i} for i in (2, 1)]


def test_export_roundtrip():
    orig = da.select
    da.select = lambda db, sql: db.query(sql)
    try:
        with tempfile.TemporaryDirectory() as d:
            store = LocalDirStore(d)
            assert da.run_export(_Db(), store, ["202001", "202002"], ["11680"]) == 0
            rows = decode(store.get("deals_202001.csv.gz"))
            assert [r["deal_key"] for r in rows] == ["k1", "k2"]
            assert rows[0]["is_cancelled"] == "0" and rows[0]["contract_month"] == "202001"
    finally:
        da.select = orig
