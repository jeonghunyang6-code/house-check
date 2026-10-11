"""원본 보관: 월별 CSV.gz 파일 (docs/HANDOFF.md 0절 "저장 방식").

파일 하나 = 종류 1개 × 계약월 1개 × 여러 시군구 (`rents_202301.csv.gz`). 같은 달에 다른 시군구를 나중에 받으면
기존 파일을 내려받아 그 시군구 행만 바꿔 끼우고(merge) 다시 올린다.

저장소
- GhReleaseStore: GitHub Releases (Actions 에서 `gh` CLI + GH_TOKEN). 릴리스당 파일 1,000개, 파일당 2GiB 미만,
  전체 용량 제한 없음 (docs.github.com "About releases", 2026-10-11 확인).
- LocalDirStore : 로컬 폴더 (테스트, 사용자 PC 백업).
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Protocol

RENT_COLUMNS = (
    "rent_key", "region_code", "contract_month", "apt_seq", "apt_name", "contract_date", "area_m2", "floor",
    "deposit_10k", "monthly_rent_10k", "contract_type", "used_renewal_right", "term_start", "term_end",
    "pre_deposit_10k", "pre_monthly_rent_10k", "first_seen_date", "last_seen_date", "disappeared",
)


def asset_name(kind: str, contract_month: str) -> str:
    return f"{kind}s_{contract_month}.csv.gz"


def _cell(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def encode(rows: Iterable[dict], columns: tuple[str, ...] = RENT_COLUMNS) -> bytes:
    """행(dict) → gzip CSV. mtime=0 이라 같은 내용이면 같은 바이트가 나온다."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow([_cell(r.get(c)) for c in columns])
    return gzip.compress(buf.getvalue().encode("utf-8"), mtime=0)


def decode(data: bytes) -> list[dict]:
    """gzip CSV → 행(dict, 값은 문자열, 빈 칸은 '')."""
    return list(csv.DictReader(io.StringIO(gzip.decompress(data).decode("utf-8"))))


def merge(existing: list[dict], new_rows: list[dict], replace_regions: set[str], key: str = "rent_key") -> list[dict]:
    """기존 파일에서 replace_regions 의 행을 빼고 새 행을 넣는다. 정렬해서 결과를 안정적으로 만든다."""
    kept = [r for r in existing if r["region_code"] not in replace_regions]
    out = kept + [{c: _cell(v) for c, v in r.items()} for r in new_rows]
    return sorted(out, key=lambda r: (r["region_code"], r[key]))


class Store(Protocol):
    def get(self, name: str) -> bytes | None: ...
    def put(self, name: str, data: bytes) -> None: ...


class LocalDirStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, name: str) -> bytes | None:
        p = self.root / name
        return p.read_bytes() if p.exists() else None

    def put(self, name: str, data: bytes) -> None:
        tmp = self.root / (name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(self.root / name)


class ArchiveError(RuntimeError):
    pass


class GhReleaseStore:
    """`gh` CLI 로 릴리스 자산을 읽고 쓴다. GH_TOKEN(contents: write)·GH_REPO 환경 변수가 필요하다."""

    def __init__(self, tag: str = "raw-data"):
        self.tag = tag
        self._assets: set[str] | None = None

    def _gh(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=600)
        if check and p.returncode != 0:
            raise ArchiveError(f"gh {args[0]} {args[1] if len(args) > 1 else ''} 실패: {p.stderr.strip()[:300]}")
        return p

    def _ensure(self) -> set[str]:
        if self._assets is None:
            p = self._gh("release", "view", self.tag, "--json", "assets", check=False)
            if p.returncode != 0:
                if "not found" not in p.stderr.lower():
                    raise ArchiveError(f"gh release view 실패: {p.stderr.strip()[:300]}")
                self._gh("release", "create", self.tag, "--title", "원본 보관 (실거래 CSV.gz)", "--prerelease",
                         "--notes", "jobs/rent_archive.py 가 관리한다. 수동으로 지우지 말 것.")
                self._assets = set()
            else:
                self._assets = {a["name"] for a in json.loads(p.stdout)["assets"]}
        return self._assets

    def get(self, name: str) -> bytes | None:
        if name not in self._ensure():
            return None
        d = tempfile.mkdtemp()
        try:
            self._gh("release", "download", self.tag, "--pattern", name, "--dir", d)
            return (Path(d) / name).read_bytes()
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def put(self, name: str, data: bytes) -> None:
        self._ensure()
        d = tempfile.mkdtemp()
        try:
            (Path(d) / name).write_bytes(data)
            self._gh("release", "upload", self.tag, str(Path(d) / name), "--clobber")
            self._assets.add(name)
        finally:
            shutil.rmtree(d, ignore_errors=True)


def open_store(spec: str | None = None) -> Store:
    """'gh' | 'gh:<tag>' | 'dir:<경로>'. 기본은 HC_ARCHIVE 환경 변수, 없으면 dir:data/archive."""
    spec = spec or os.environ.get("HC_ARCHIVE", "dir:data/archive")
    if spec == "gh" or spec.startswith("gh:"):
        return GhReleaseStore(spec[3:] or "raw-data")
    if spec.startswith("dir:"):
        return LocalDirStore(spec[4:])
    raise ValueError(f"unknown archive store {spec!r}")
