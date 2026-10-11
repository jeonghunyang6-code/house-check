"""Supabase(Postgres) 접근. 추가 패키지 없이 두 경로를 쓴다 (docs/HANDOFF.md 0절).

- api : Supabase 관리 API `POST /v1/projects/{ref}/database/query` (HTTPS).
        클라우드 세션은 5432·6543 포트가 막혀 이 경로만 된다. SUPABASE_ACCESS_TOKEN + DATABASE_URL(ref 추출용).
- psql: `psql "$DATABASE_URL"` 하위 프로세스. GitHub Actions 러너용 (러너에서의 접속은 미검증).

SQL은 문자열로 만든다(관리 API에 파라미터 바인딩이 있는지 확인하지 못함). 값은 반드시 lit()로 감싼다.
토큰·DATABASE_URL 값은 예외 메시지와 로그에 싣지 않는다.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import date
from typing import Protocol


class DbError(RuntimeError):
    pass


def lit(v: object) -> str:
    """Python 값 → SQL 리터럴. standard_conforming_strings=on(Postgres 기본) 전제."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("non-finite float")
        return repr(v)
    if isinstance(v, date):
        return f"'{v.isoformat()}'::date"
    if isinstance(v, str):
        if "\x00" in v:
            raise ValueError("NUL in string")
        return "'" + v.replace("'", "''") + "'"
    raise TypeError(f"unsupported type {type(v).__name__}")


class Db(Protocol):
    def query(self, sql: str) -> list[dict]:
        """SQL(여러 문장 가능)을 실행하고 마지막 문장의 결과 행을 돌려준다."""


def project_ref(database_url: str) -> str:
    m = re.match(r"postgres(?:ql)?://postgres\.([a-z0-9]{20})[:@]", database_url)
    if not m:
        raise DbError("DATABASE_URL 에서 프로젝트 ref 를 찾지 못함 (형식: postgresql://postgres.<ref>:...)")
    return m.group(1)


class ApiDb:
    def __init__(self, token: str, ref: str, timeout: int = 120):
        self._token, self._url, self._timeout = token, f"https://api.supabase.com/v1/projects/{ref}/database/query", timeout

    def query(self, sql: str) -> list[dict]:
        req = urllib.request.Request(
            self._url,
            data=json.dumps({"query": sql}).encode(),
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                return json.loads(r.read() or b"[]")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            raise DbError(f"HTTP {e.code}: {body}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            raise DbError(f"connection failed: {type(e).__name__}") from None


class PsqlDb:
    """행이 필요한 SELECT 는 select() 로 감싸 JSON 한 줄로 받는다. 행이 없는 문장(DDL·DML)은 []."""

    def __init__(self, database_url: str, timeout: int = 300):
        self._url, self._timeout = database_url, timeout

    def query(self, sql: str) -> list[dict]:
        p = subprocess.run(
            ["psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1", "-d", self._url],
            input=sql, capture_output=True, text=True, timeout=self._timeout,
        )
        if p.returncode != 0:
            raise DbError(f"psql exit {p.returncode}: {p.stderr.strip()[:500]}")
        lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
        if not lines:
            return []
        try:
            out = json.loads(lines[-1])
        except json.JSONDecodeError:
            raise DbError("psql 출력의 마지막 줄이 JSON 이 아님 (select() 로 감쌌는지 확인)") from None
        if not isinstance(out, list):
            raise DbError("psql 출력이 JSON 배열이 아님")
        return out


def rows_json(select_sql: str) -> str:
    """두 경로에서 같은 모양(list[dict])을 받도록 SELECT 를 JSON 배열 한 줄로 감싼다."""
    # json_agg 는 여러 줄로 출력되므로 jsonb::text 로 한 줄을 보장한다
    return f"SELECT coalesce(jsonb_agg(t), '[]'::jsonb)::text AS j FROM ({select_sql}) t"


def select(db: Db, select_sql: str) -> list[dict]:
    if isinstance(db, PsqlDb):
        return db.query(rows_json(select_sql) + ";")
    return db.query(select_sql)


def connect(backend: str | None = None) -> Db:
    """backend: 'api' | 'psql' | None(HC_DB_BACKEND 환경 변수, 없으면 api)."""
    backend = backend or os.environ.get("HC_DB_BACKEND", "api")
    url = os.environ.get("DATABASE_URL", "")
    if backend == "psql":
        if not url:
            raise DbError("DATABASE_URL 이 설정되지 않음")
        return PsqlDb(url)
    if backend == "api":
        token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
        if not token:
            raise DbError("SUPABASE_ACCESS_TOKEN 이 설정되지 않음")
        ref = os.environ.get("SUPABASE_PROJECT_REF") or project_ref(url)
        return ApiDb(token, ref)
    raise DbError(f"unknown backend {backend}")
