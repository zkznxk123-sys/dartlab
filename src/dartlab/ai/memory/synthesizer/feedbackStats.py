"""feedback_*.md 통계 합성기 — read-only.

측정 항목:
- 파일 수, 총 본문 길이, 평균 길이
- frontmatter 추출 (name / description / type / originSessionId)
- `[[name]]` 링크 그래프 (in-degree top-N)
- 본문 한국어/영어 토큰 빈도 top-N (description 가중)
- type 분포

산출: 입력 디렉토리 안 `_synth/feedbackStats.md`. 운영자가 본 자료를 main agent
에게 넘겨 의미 합성 → cherry-pick 으로 `MEMORY.md` 흡수. 자동 흡수 없음.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_LINK_RE = re.compile(r"\[\[([a-zA-Z0-9_\-]+)\]\]")
_KO_TOKEN_RE = re.compile(r"[가-힣]{2,}")
_EN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
_STOPWORDS_KO = {
    "그리고",
    "그러나",
    "하지만",
    "또한",
    "때문",
    "이거",
    "그것",
    "이것",
    "저것",
    "사용",
    "사용자",
    "메모리",
    "이미",
    "지금",
    "여기",
    "거기",
    "처음",
    "마지막",
    "경우",
    "상황",
    "이후",
    "이전",
    "동안",
    "위해",
    "통해",
    "대해",
    "관련",
}
_STOPWORDS_EN = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "these",
    "those",
    "into",
    "onto",
    "have",
    "has",
    "had",
    "been",
    "was",
    "were",
    "are",
    "is",
    "be",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "as",
    "or",
    "but",
    "not",
    "no",
    "if",
    "do",
    "does",
    "did",
    "can",
    "could",
    "should",
    "would",
    "will",
}


@dataclass
class FeedbackStats:
    """feedback_*.md 통계 합성 결과."""

    file_count: int
    total_chars: int
    avg_chars: float
    type_distribution: dict[str, int]
    link_in_degree: list[tuple[str, int]]  # name → in-degree, top-N
    ko_top_tokens: list[tuple[str, int]]
    en_top_tokens: list[tuple[str, int]]
    files: list[dict[str, Any]] = field(default_factory=list)


def _parseFile(path: Path) -> dict[str, Any] | None:
    """단일 .md 파일 파싱 — frontmatter dict + body str. 실패 시 None."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    fm_text, body = match.group(1), match.group(2)
    try:
        frontmatter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(frontmatter, dict):
        return None
    return {
        "path": path,
        "name": frontmatter.get("name") or path.stem,
        "description": frontmatter.get("description") or "",
        "type": (frontmatter.get("metadata") or {}).get("type") or frontmatter.get("type") or "unknown",
        "originSessionId": (frontmatter.get("metadata") or {}).get("originSessionId")
        or frontmatter.get("originSessionId"),
        "body": body,
    }


def _tokens(text: str, *, regex: re.Pattern, stopwords: set[str]) -> list[str]:
    tokens = regex.findall(text or "")
    return [
        t.lower() if not _KO_TOKEN_RE.match(t) else t
        for t in tokens
        if (t.lower() if not _KO_TOKEN_RE.match(t) else t) not in stopwords
    ]


def synthFeedbackStats(
    memoryDir: Path,
    *,
    pattern: str = "feedback_*.md",
    topN: int = 20,
    writeReport: bool = True,
) -> FeedbackStats:
    """memoryDir 안 feedback_*.md 통계 합성.

    Args:
        memoryDir: feedback 파일들이 있는 디렉토리.
        pattern: 매칭 글롭. 기본 'feedback_*.md'.
        topN: link 그래프 + 토큰 빈도 반환 상위 N.
        writeReport: True 면 memoryDir/_synth/feedbackStats.md 작성.

    Returns:
        FeedbackStats 합성 결과.
    """
    files = sorted(memoryDir.glob(pattern))
    parsed: list[dict[str, Any]] = []
    for path in files:
        entry = _parseFile(path)
        if entry is not None:
            parsed.append(entry)

    file_count = len(parsed)
    total_chars = sum(len(p["body"]) for p in parsed)
    avg_chars = total_chars / file_count if file_count else 0.0

    type_dist: Counter[str] = Counter()
    link_counts: Counter[str] = Counter()
    ko_counts: Counter[str] = Counter()
    en_counts: Counter[str] = Counter()

    for entry in parsed:
        type_dist[entry["type"]] += 1
        body = entry["body"]
        desc = entry["description"] or ""

        for link in _LINK_RE.findall(body):
            link_counts[link.replace("-", "_")] += 1

        # description 은 가중치 2× — 핵심 의미 압축
        for _ in range(2):
            for tok in _tokens(desc, regex=_KO_TOKEN_RE, stopwords=_STOPWORDS_KO):
                ko_counts[tok] += 1
            for tok in _tokens(desc, regex=_EN_TOKEN_RE, stopwords=_STOPWORDS_EN):
                en_counts[tok] += 1
        for tok in _tokens(body, regex=_KO_TOKEN_RE, stopwords=_STOPWORDS_KO):
            ko_counts[tok] += 1
        for tok in _tokens(body, regex=_EN_TOKEN_RE, stopwords=_STOPWORDS_EN):
            en_counts[tok] += 1

    stats = FeedbackStats(
        file_count=file_count,
        total_chars=total_chars,
        avg_chars=avg_chars,
        type_distribution=dict(type_dist),
        link_in_degree=link_counts.most_common(topN),
        ko_top_tokens=ko_counts.most_common(topN),
        en_top_tokens=en_counts.most_common(topN),
        files=[{"name": p["name"], "type": p["type"], "chars": len(p["body"])} for p in parsed],
    )

    if writeReport:
        _writeMarkdownReport(memoryDir, stats)

    return stats


def _writeMarkdownReport(memoryDir: Path, stats: FeedbackStats) -> Path:
    """_synth/feedbackStats.md 작성. 원본 feedback_*.md 절대 수정 안 함."""
    synth_dir = memoryDir / "_synth"
    synth_dir.mkdir(exist_ok=True)
    output = synth_dir / "feedbackStats.md"

    lines: list[str] = [
        "# feedback_*.md 통계 합성 (read-only)",
        "",
        f"생성: {datetime.now(timezone.utc).isoformat()}",
        f"입력: `{memoryDir}`",
        "",
        "**주의**: 본 파일은 read-only 통계. 의미 합성은 운영자가 main agent 에 요청 후 cherry-pick 으로 `MEMORY.md` 흡수.",
        "",
        "## 1. 요약",
        "",
        f"- 파일 수: **{stats.file_count}**",
        f"- 총 본문 길이: {stats.total_chars:,} chars",
        f"- 평균 길이: {stats.avg_chars:.0f} chars/file",
        "",
        "## 2. type 분포",
        "",
    ]
    for tp, cnt in sorted(stats.type_distribution.items(), key=lambda x: -x[1]):
        lines.append(f"- `{tp}`: {cnt}")
    lines.append("")

    lines.extend(["## 3. 링크 그래프 (in-degree top)", "", "다른 메모리에서 `[[name]]` 으로 참조된 횟수.", ""])
    if stats.link_in_degree:
        for name, deg in stats.link_in_degree:
            lines.append(f"- `{name}`: {deg}")
    else:
        lines.append("- (참조 0)")
    lines.append("")

    lines.extend(["## 4. 한국어 토큰 빈도 top", "", "description (가중 2×) + body 토큰 빈도.", ""])
    for tok, cnt in stats.ko_top_tokens:
        lines.append(f"- `{tok}`: {cnt}")
    lines.append("")

    lines.extend(["## 5. 영문 토큰 빈도 top", ""])
    for tok, cnt in stats.en_top_tokens:
        lines.append(f"- `{tok}`: {cnt}")
    lines.append("")

    lines.extend(
        [
            "## 6. 파일별 길이",
            "",
            "| name | type | chars |",
            "|---|---|---:|",
        ]
    )
    for entry in sorted(stats.files, key=lambda e: -int(e["chars"])):
        lines.append(f"| {entry['name']} | {entry['type']} | {entry['chars']} |")
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="feedback_*.md 통계 합성 (read-only)")
    parser.add_argument("memoryDir", type=Path, help="feedback 파일들이 있는 디렉토리")
    parser.add_argument("--pattern", default="feedback_*.md")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--no-write", action="store_true", help="리포트 작성 없이 통계만 출력")
    args = parser.parse_args()

    stats = synthFeedbackStats(args.memoryDir, pattern=args.pattern, topN=args.top, writeReport=not args.no_write)
    print(f"file_count={stats.file_count} total_chars={stats.total_chars} avg={stats.avg_chars:.0f}")
    if not args.no_write:
        print(f"리포트: {args.memoryDir / '_synth' / 'feedbackStats.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
