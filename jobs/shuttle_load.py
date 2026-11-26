"""회사 셔틀 노선표 CSV → shuttle_stops (통상 근무 출근 승차·퇴근 하차만). 회사 내부 자료: CSV 는 저장소에 두지 말 것.

    python -m jobs.shuttle_load 노선표.csv [--dry-run]

CSV 열: 캠퍼스,노선형태,지역,노선명,회차,근무구분,운행,순번,정류장명,시각,승하차,위도,경도,카카오맵
표를 통째로 바꾼다(한 트랜잭션). 출력에는 개수만(정류장 이름·좌표는 로그에 남기지 않음)."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict

from collector.db import connect, lit


def route_name(s: str) -> str:
    return s.split(" (")[0].strip()


def parse(path: str) -> tuple[list[tuple], list[tuple]]:
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    trips: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["노선형태"] in ("출근", "퇴근") and r["근무구분"].strip() == "통상":
            trips[(r["노선형태"], r["노선명"], r["회차"].strip(), r["운행"])].append(r)
    o: dict[tuple, tuple[str, str]] = {}
    h: dict[tuple, set[str]] = defaultdict(set)
    for (kind, rt, hc, _), rs in trips.items():
        rs.sort(key=lambda r: int(r["순번"]))
        if kind == "출근":
            arr = [r["시각"] for r in rs if "하차" in r["승하차"]]
            arr = arr[-1] if arr else ""
            for r in rs:
                if "승차" in r["승하차"] and "회사" not in r["정류장명"]:
                    k = (r["정류장명"].strip(), round(float(r["위도"]), 5), round(float(r["경도"]), 5), route_name(rt))
                    if k not in o or r["시각"] < o[k][0]:
                        o[k] = (r["시각"], arr)
        else:
            dep = [r["시각"] for r in rs if "승차" in r["승하차"] and "회사" in r["정류장명"]]
            hh = (dep[0] if dep else hc.replace("통상", "").replace("퇴근", "").strip())[:2]
            for r in rs:
                if "하차" in r["승하차"] and "회사" not in r["정류장명"]:
                    h[(r["정류장명"].strip(), round(float(r["위도"]), 5), round(float(r["경도"]), 5), route_name(rt))].add(hh)
    return ([(*k, v[0], v[1]) for k, v in o.items()], [(*k, ",".join(sorted(v))) for k, v in h.items()])


def load_sql(o: list[tuple], h: list[tuple]) -> str:
    vals = [f"('o', {lit(n)}, {la}, {lo}, {lit(rt)}, {lit(tb)}, {lit(ta)}, NULL)" for n, la, lo, rt, tb, ta in o] + \
           [f"('h', {lit(n)}, {la}, {lo}, {lit(rt)}, NULL, NULL, {lit(hs)})" for n, la, lo, rt, hs in h]
    return ("BEGIN; DELETE FROM shuttle_stops; "
            + (f"INSERT INTO shuttle_stops (kind, name, lat, lng, route, t_board, t_arrive, hours) VALUES {', '.join(vals)}; " if vals else "")
            + "COMMIT;")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    o, h = parse(a.csv)
    print(f"[shuttle] 출근 승차 {len(o)} · 퇴근 하차 {len(h)}")
    if not a.dry_run:
        connect().query(load_sql(o, h))
        print("[shuttle] 저장 완료")


if __name__ == "__main__":
    main()
