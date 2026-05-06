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
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9_]+")


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


_STOCK_CODE_RE = re.compile(r"\b\d{6}\b")
_RECIPE_TAG_PREFIX = "skill:engines.recipe."
_TARGET_TAG_PREFIX = "target:"
_METRIC_TAG_PREFIX = "metric:"


def _scoreRecall(row: dict, q_tokens: set[str], q_meta: dict) -> float:
    """recall 점수 — 토큰 overlap + target/skill category/metric 가중.

    가중치:
    - target:{stockCode} 일치: +0.3
    - skill:engines.recipe.* 태그: +0.2 (recipe 우선 회상)
    - metric:{name} 이 query 토큰에 포함: +0.2 (특정 지표 회상)
    """
    d_tokens = _tokenize(row.get("text", ""))
    if not d_tokens:
        return 0.0
    overlap = len(q_tokens & d_tokens)
    base = overlap / (len(q_tokens) + 1) if overlap else 0.0
    if base == 0.0:
        return 0.0

    bonus = 0.0
    tags = row.get("tags") or []
    if isinstance(tags, list):
        target_codes = q_meta.get("targets") or set()
        for tag in tags:
            tag_str = str(tag)
            if tag_str.startswith(_TARGET_TAG_PREFIX):
                code = tag_str[len(_TARGET_TAG_PREFIX) :]
                if code in target_codes:
                    bonus += 0.3
                    break
        if any(str(t).startswith(_RECIPE_TAG_PREFIX) for t in tags):
            bonus += 0.2
        for tag in tags:
            tag_str = str(tag)
            if tag_str.startswith(_METRIC_TAG_PREFIX):
                metric = tag_str[len(_METRIC_TAG_PREFIX) :].lower()
                if metric and any(metric in tok for tok in q_tokens):
                    bonus += 0.2
                    break
    return base + bonus


def _extractQueryMeta(query: str) -> dict:
    return {
        "targets": set(_STOCK_CODE_RE.findall(query or "")),
    }


def recall(query: str, *, k: int = 5) -> list[dict]:
    if not _DECISIONS_PATH.exists() or not query:
        return []
    q_tokens = _tokenize(query)
    q_meta = _extractQueryMeta(query)
    scored: list[tuple[float, dict]] = []
    with _DECISIONS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            score = _scoreRecall(row, q_tokens, q_meta)
            if score > 0.0:
                scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[: max(1, int(k or 5))]]


def setDecisionsPathForTesting(path: Path) -> None:
    global _DECISIONS_PATH
    _DECISIONS_PATH = path
