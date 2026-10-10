"""수집한 자막에서 시세 해석과 관련된 영상·구간을 키워드로 추린다.

사용법:
    python -m tools.insight_crawler.triage                  # 주제별 영상 순위
    python -m tools.insight_crawler.triage --topic 거래량    # 해당 주제 구간 발췌 출력

출력: data/raw/triage/<topic>.md  (영상 링크 &t=초 포함)
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from .crawl import OUT_DIR

TRIAGE_DIR = OUT_DIR.parent / "triage"

# 분석기 지표와 연결되는 주제별 키워드
TOPICS: dict[str, list[str]] = {
    "거래량": ["거래량", "거래가 줄", "거래가 늘", "거래가 없", "거래 절벽", "매물이 잠"],
    "신고가·실거래": ["신고가", "전고점", "실거래", "호가", "급매"],
    "전세·월세": ["전세가", "전세 가격", "전셋값", "전세가율", "월세", "전월세", "갭"],
    "금리·유동성": ["금리", "유동성", "통화량", "m2", "대출", "dsr", "스트레스"],
    "공급·입주": ["입주 물량", "입주물량", "공급", "인허가", "착공", "미분양"],
    "규제·정책": ["토지거래허가", "토허", "규제", "양도세", "취득세", "다주택", "실거주 의무"],
    "상급지·양극화": ["상급지", "하급지", "양극화", "갈아타", "중심지", "강남"],
    "사이클·국면": ["상승장", "하락장", "바닥", "고점", "조정", "사이클", "폭락", "반등"],
    "입지·호재": ["지하철", "역세권", "호재", "gtx", "일자리", "학군", "신축", "재건축", "재개발"],
}


def load_transcripts() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(OUT_DIR.glob("*.json"))
    ]


def windows(segments: list[dict], idx: int, before: int = 2, after: int = 4) -> str:
    lo, hi = max(0, idx - before), min(len(segments), idx + after + 1)
    return " ".join(s["text"] for s in segments[lo:hi])


def rank(transcripts: list[dict]) -> dict[str, list[tuple[int, dict]]]:
    out: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for tr in transcripts:
        text = " ".join(s["text"] for s in tr["segments"]).lower()
        title = (tr.get("title") or "").lower()
        for topic, kws in TOPICS.items():
            score = sum(text.count(k) for k in kws) + 5 * sum(title.count(k) for k in kws)
            if score:
                out[topic].append((score, tr))
    for topic in out:
        out[topic].sort(key=lambda x: -x[0])
    return out


def excerpt(transcripts: list[dict], topic: str, top: int) -> Path:
    kws = TOPICS[topic]
    pat = re.compile("|".join(map(re.escape, kws)), re.IGNORECASE)
    ranked = rank(transcripts)[topic][:top]
    lines = [f"# {topic} — 상위 {len(ranked)}개 영상 발췌\n"]
    for score, tr in ranked:
        lines.append(f"## [{tr['upload_date']}] {tr['title']} (score {score})\n")
        last_t = -60.0
        for i, seg in enumerate(tr["segments"]):
            if pat.search(seg["text"]) and seg["t"] - last_t >= 20:
                t = int(seg["t"])
                lines.append(f"- [{t // 60}:{t % 60:02d}]({tr['url']}&t={t}) {windows(tr['segments'], i)}")
                last_t = seg["t"]
        lines.append("")
    TRIAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = TRIAGE_DIR / f"{topic.replace('·', '_')}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", choices=list(TOPICS) + ["all"])
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    transcripts = [t for t in load_transcripts() if t["segments"]]
    if not args.topic:
        for topic, items in rank(transcripts).items():
            print(f"\n## {topic}: {len(items)}개 영상")
            for score, tr in items[:8]:
                print(f"  {score:4d}  {tr['upload_date']}  {tr['title']}")
        return
    topics = list(TOPICS) if args.topic == "all" else [args.topic]
    for topic in topics:
        print(excerpt(transcripts, topic, args.top))


if __name__ == "__main__":
    main()
