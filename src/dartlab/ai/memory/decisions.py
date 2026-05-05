"""세션 간 recall / remember.

저장: ~/.dartlab/ai_memory/decisions.jsonl (append-only).
검색: 단순 BM25-like — 질문 토큰 매칭 빈도. 임베딩은 P5.1.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_DECISIONS_PATH = Path.home() / ".dartlab" / "ai_memory" / "decisions.jsonl"
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


@dataclass
class Decision:
    text: str
    tags: list[str] = field(default_factory=list)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _ensureDir() -> None:
    _DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)


def remember(text: str, *, tags: list[str] | None = None) -> None:
    if not text or not text.strip():
        return
    _ensureDir()
    decision = Decision(text=text.strip(), tags=tags or [])
    with _DECISIONS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(decision), ensure_ascii=False) + "\n")


def _tokenize(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(text or "")}


def recall(query: str, *, k: int = 5) -> list[dict]:
    if not _DECISIONS_PATH.exists() or not query:
        return []
    q_tokens = _tokenize(query)
    scored: list[tuple[float, dict]] = []
    with _DECISIONS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            d_tokens = _tokenize(row.get("text", ""))
            if not d_tokens:
                continue
            overlap = len(q_tokens & d_tokens)
            if overlap == 0:
                continue
            score = overlap / (len(q_tokens) + 1)
            scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[: max(1, int(k or 5))]]


def setDecisionsPathForTesting(path: Path) -> None:
    global _DECISIONS_PATH
    _DECISIONS_PATH = path
