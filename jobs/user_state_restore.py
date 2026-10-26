"""개인 기록 백업 되살리기 (backup.yml 이 Releases 'backup' 에 올린 user_state_YYYYMMDD.json.gz.enc).

    HC_KEY=문구 python -m jobs.user_state_restore user_state_20261101.json.gz.enc          # 내용만 보기
    HC_KEY=문구 python -m jobs.user_state_restore user_state_20261101.json.gz.enc --write  # DB user_state 에 덮어쓰기(키별)
    HC_KEY=문구 python -m jobs.user_state_restore user_state_20261101.json.gz.enc --check  # 되살리기 시험: 지금 DB 와 키별 비교(쓰지 않음, backup.yml 이 올린 뒤 매번)

복호화는 openssl(backup.yml 과 같은 옵션). HC_KEY 는 환경 변수로만 받고 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
import sys

from collector.db import DbError, connect, lit, select


def decrypt(path: str) -> dict:
    if not os.environ.get("HC_KEY"):
        raise SystemExit("HC_KEY 환경 변수가 없습니다")
    p = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:HC_KEY", "-in", path],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit("복호화 실패(문구가 다르거나 파일이 깨짐)")
    return json.loads(gzip.decompress(p.stdout))


def check(backup: dict, now: dict) -> int:
    """키마다 백업 = 지금 인지. 값은 출력하지 않는다(개인 기록). 백업 뒤 바뀐 키는 '다름'(실패 아님), 빠진 키만 실패."""
    def norm(v):   # psql 은 jsonb 를 글자로, api 는 값으로 돌려준다
        try:
            return json.loads(v) if isinstance(v, str) else v
        except ValueError:
            return v
    missing = sorted(set(now) - set(backup))
    for k in sorted(set(now) | set(backup)):
        print(f"  {k}: {'같음' if k in backup and k in now and norm(now[k]) == backup[k] else '백업에 없음' if k not in backup else '지금 없음' if k not in now else '다름(백업 뒤 바뀜)'}")
    print(f"  되살리기 시험: 백업 키 {len(backup)}개 · 지금 키 {len(now)}개 · 빠진 키 {len(missing)}개 → {'실패' if missing else '정상'}")
    return 1 if missing or not backup else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 지금 DB 와 비교. 지금 있는 키가 백업에 없으면 실패(1)")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    data = decrypt(a.file)
    for k, v in sorted(data.items()):
        n = len(v) if isinstance(v, (list, dict)) else 1
        print(f"  {k}: {type(v).__name__} {n}")
    if a.check:
        return check(data, {r["k"]: r["v"] for r in select(connect(a.db), "SELECT k, v FROM user_state")})
    if a.write:
        try:
            connect(a.db).query("INSERT INTO user_state (k, v) VALUES " + ", ".join(
                f"({lit(k)}, {lit(json.dumps(v, ensure_ascii=False))}::jsonb)" for k, v in data.items())
                + " ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now();")
        except DbError as e:
            print(f"[restore] 실패: {e}", file=sys.stderr)
            return 1
        print(f"  {len(data)}개 키를 되살렸습니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
