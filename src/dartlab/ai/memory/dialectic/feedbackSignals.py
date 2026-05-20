"""사용자 발화 시그널 자기-학습 — 부정·긍정 발화 원문 추출.

sessionIndex.db 의 user entries 에서 *짧은 부정/긍정 발화* 를 키워드 매칭으로
추출. LLM 분류 없이 결정론 휴리스틱. 추출된 *원문* 을 system prompt 에 부착하면
LLM 이 맥락 파악해 회피·강화 시그널로 활용.

논리:
- 짧고 명확한 발화 (≤30 chars) 가 시그널 강함 — 긴 발화는 *맥락 설명* 이라 분류 모호.
- 부정/긍정 키워드 substring 매칭 + 길이 임계.
- 최근 N 개만 — 오래된 시그널은 컨텍스트 부정확.
- 캐시 7 일 TTL.

dartlab outcome ground truth 와 결: *측정 가능한 신호* 만 (LLM 분류 X), *원문 그대로*
인용 (해석은 답변 LLM 위임).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dartlab.ai.memory.sessionIndex import sessionIndexPath

_CACHE_DEFAULT = Path.home() / ".dartlab" / "ai_memory" / "feedbackSignals.cache.json"
_CACHE_TTL_SECONDS = 7 * 24 * 3600

# 부정 시그널 키워드 — 짜증·혼란·정정·반대
_NEGATIVE_KEYWORDS = (
    "무슨말",
    "이해가 안",
    "이게 무슨",
    "씨발",
    "뭔소리",
    "뭐 어쨌",
    "그게 아니라",
    "다시",
    "정정",
    "철회",
    "취소",
    "잘못",
    "틀렸",
    "왜 그래",
    "뭐냐",
    "뭐라",
    "장황",
    "쓸데없",
    "필요없",
    "장난해",
    "그만",
    "스톱",
    "그래서",
    "결국",
)

# 긍정 시그널 키워드 — 동의·확인·진행
_POSITIVE_KEYWORDS = (
    "좋다",
    "좋네",
    "맞다",
    "맞네",
    "그렇지",
    "옳다",
    "정확",
    "오케이",
    "ok",
    "굳",
    "잘했",
    "잘된",
    "잘됐",
    "진행",
    "박아",
    "해봐",
    "해라",
    "고",
    "고고",
)

# 발화 길이 임계 — 너무 길면 *맥락 설명* 이라 시그널 모호
_MAX_SIGNAL_LEN = 40
# 너무 짧으면 noise (typo)
# 한국어 강 시그널 "좋다" "맞다" "굳" 등 2 chars 도 포함 — _TRIVIAL_RE 가 ㅋㅋ/ㅎㅎ 차단.
_MIN_SIGNAL_LEN = 2

# 정규식 — 너무 단순한 발화 (인사·요청만) 제외
_TRIVIAL_RE = re.compile(r"^(안녕|hi|hello|test|테스트|ㅋ+|ㅎ+|\.\.\.|ㅠ+)$", re.IGNORECASE)


@dataclass
class FeedbackSignals:
    """발화 시그널 추출 결과."""

    negatives: list[str] = field(default_factory=list)
    positives: list[str] = field(default_factory=list)
    sample_size: int = 0
    generated_at: float = 0.0


def _cachePath() -> Path:
    env = os.environ.get("DARTLAB_FEEDBACK_SIGNALS_CACHE_PATH")
    return Path(env) if env else _CACHE_DEFAULT


def _loadCache(path: Path) -> FeedbackSignals | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("generated_at") or 0.0) > _CACHE_TTL_SECONDS:
            return None
        return FeedbackSignals(
            negatives=list(data.get("negatives") or []),
            positives=list(data.get("positives") or []),
            sample_size=int(data.get("sample_size") or 0),
            generated_at=float(data.get("generated_at") or 0.0),
        )
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def _saveCache(path: Path, signals: FeedbackSignals) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(signals), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _streamRecentUserTexts(dbPath: Path, *, limit: int = 2000) -> list[str]:
    """sessionIndex.db 에서 최근 N user text 발화 (timestamp 내림차순)."""
    if not dbPath.exists():
        return []
    try:
        conn = sqlite3.connect(dbPath)
        rows = conn.execute(
            "SELECT text FROM entries WHERE role = 'user' AND block_type = 'text' ORDER BY entry_id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        conn.close()
        return [str(r[0]) for r in rows if r and r[0]]
    except sqlite3.OperationalError:
        return []


def _isSignal(text: str, keywords: tuple[str, ...]) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if len(cleaned) < _MIN_SIGNAL_LEN or len(cleaned) > _MAX_SIGNAL_LEN:
        return False
    if _TRIVIAL_RE.match(cleaned):
        return False
    lower = cleaned.lower()
    return any(kw in cleaned or kw in lower for kw in keywords)


def extractFeedbackSignals(
    *,
    dbPath: Path | None = None,
    forceRefresh: bool = False,
    sampleLimit: int = 2000,
    topNegatives: int = 10,
    topPositives: int = 5,
) -> FeedbackSignals:
    """부정·긍정 발화 추출.

    Args:
        dbPath: sessionIndex.db 경로. None 이면 표준 위치.
        forceRefresh: True 면 캐시 무시.
        sampleLimit: 검사할 최근 user entries 개수.
        topNegatives: 부정 시그널 반환 최대 개수 (최근 순).
        topPositives: 긍정 시그널 반환 최대 개수 (최근 순).

    Returns:
        FeedbackSignals. 발화 원문 그대로 (정제만 strip).
    """
    cache = _cachePath()
    if not forceRefresh:
        cached = _loadCache(cache)
        if cached is not None:
            return cached

    db = dbPath or sessionIndexPath()
    texts = _streamRecentUserTexts(db, limit=sampleLimit)

    negatives: list[str] = []
    positives: list[str] = []
    seen_neg: set[str] = set()
    seen_pos: set[str] = set()

    for text in texts:
        clean = text.strip()
        if _isSignal(clean, _NEGATIVE_KEYWORDS) and clean not in seen_neg:
            negatives.append(clean)
            seen_neg.add(clean)
        if _isSignal(clean, _POSITIVE_KEYWORDS) and clean not in seen_pos:
            positives.append(clean)
            seen_pos.add(clean)
        if len(negatives) >= topNegatives and len(positives) >= topPositives:
            break

    signals = FeedbackSignals(
        negatives=negatives[:topNegatives],
        positives=positives[:topPositives],
        sample_size=len(texts),
        generated_at=time.time(),
    )
    _saveCache(cache, signals)
    return signals


__all__ = ["FeedbackSignals", "extractFeedbackSignals"]
