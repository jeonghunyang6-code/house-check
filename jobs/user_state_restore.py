"""개인 기록 백업 되살리기 (backup.yml 이 Releases 'backup' 에 올린 user_state_YYYYMMDD.json.gz.enc).

    HC_KEY=문구 python -m jobs.user_state_restore user_state_20261101.json.gz.enc          # 내용만 보기
    HC_KEY=문구 python -m jobs.user_state_restore user_state_20261101.json.gz.enc --write  # DB user_state 에 덮어쓰기(키별)

복호화는 openssl(backup.yml 과 같은 옵션). HC_KEY 는 환경 변수로만 받고 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
import sys

from collector.db import DbError, connect, lit


def decrypt(path: str) -> dict:
    if not os.environ.get("HC_KEY"):
        raise SystemExit("HC_KEY 환경 변수가 없습니다")
    p = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:HC_KEY", "-in", path],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit("복호화 실패(문구가 다르거나 파일이 깨짐)")
    return json.loads(gzip.decompress(p.stdout))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--db", choices=["api", "psql"])
    a = ap.parse_args(argv)
    data = decrypt(a.file)
    for k, v in sorted(data.items()):
        n = len(v) if isinstance(v, (list, dict)) else 1
        print(f"  {k}: {type(v).__name__} {n}")
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
