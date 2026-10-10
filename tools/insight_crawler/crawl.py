"""유튜브 채널 영상의 메타데이터와 한국어 자막을 수집해 타임스탬프 단위 텍스트로 저장한다.

출처 추적이 목적이므로 모든 문장은 (video_id, 시작초)로 원본 위치를 되짚을 수 있게 남긴다.

사용법:
    python -m tools.insight_crawler.crawl                       # 기본 채널(@thewriter-song) 전체
    python -m tools.insight_crawler.crawl --limit 5             # 최신 5개만
    python -m tools.insight_crawler.crawl --url https://www.youtube.com/watch?v=XXXX

출력 (data/raw/는 .gitignore 대상):
    data/raw/youtube/<video_id>.ko.vtt        원본 자막
    data/raw/youtube/<video_id>.info.json     원본 메타데이터
    data/raw/transcripts/<video_id>.json      정제된 타임스탬프 텍스트
    data/raw/transcripts/index.csv            영상 목록
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .vtt import parse_vtt

DEFAULT_CHANNEL = "https://www.youtube.com/@thewriter-song/videos"
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "youtube"
OUT_DIR = ROOT / "data" / "raw" / "transcripts"


def download(urls: list[str], limit: int | None) -> None:
    import yt_dlp

    opts = {
        "skip_download": True,
        "writesubtitles": True,          # 업로더가 직접 올린 자막 우선
        "writeautomaticsub": True,       # 없으면 자동 생성 자막
        "subtitleslangs": ["ko"],
        "subtitlesformat": "vtt",
        "writeinfojson": True,
        "outtmpl": str(RAW_DIR / "%(id)s.%(ext)s"),
        "download_archive": str(RAW_DIR / "archive.txt"),  # 재실행 시 신규 영상만
        "ignoreerrors": True,
        "sleep_interval_requests": 1,
    }
    if limit:
        opts["playlistend"] = limit
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download(urls)


def build_transcripts() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for info_path in sorted(RAW_DIR.glob("*.info.json")):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        vid = info["id"]
        vtt_path = RAW_DIR / f"{vid}.ko.vtt"
        segments = parse_vtt(vtt_path.read_text(encoding="utf-8")) if vtt_path.exists() else []
        record = {
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": info.get("title"),
            "channel": info.get("channel"),
            "upload_date": info.get("upload_date"),
            "duration": info.get("duration"),
            "description": info.get("description"),
            "caption_kind": "manual" if "ko" in (info.get("subtitles") or {}) else "auto",
            "segments": segments,
        }
        (OUT_DIR / f"{vid}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        rows.append([vid, record["upload_date"], record["title"], len(segments), record["url"]])

    with (OUT_DIR / "index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "upload_date", "title", "segments", "url"])
        w.writerows(sorted(rows, key=lambda r: r[1] or "", reverse=True))
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", help="채널 또는 영상 URL (여러 번 지정 가능)")
    ap.add_argument("--limit", type=int, help="채널에서 최신 N개만")
    ap.add_argument("--skip-download", action="store_true", help="이미 받은 파일로 정제만 다시 실행")
    args = ap.parse_args()

    if not args.skip_download:
        download(args.url or [DEFAULT_CHANNEL], args.limit)
    n = build_transcripts()
    print(f"transcripts: {n} videos -> {OUT_DIR}")


if __name__ == "__main__":
    main()
