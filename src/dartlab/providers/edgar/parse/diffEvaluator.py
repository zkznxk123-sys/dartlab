"""SEC 10-K / 10-Q period-over-period diff evaluator.

두 연속 period 의 동일 section 텍스트 차이 정량화. dart/parse/diffEvaluator
의 SEC 등가 — 본 wrapper 는 SEC iXBRL 구조 (section 분리가 dart 보다 명확)
기반 thin diff.

핵심 지표:
- ``textSimilarity`` (0.0~1.0): Jaccard token similarity
- ``addedTokens`` / ``removedTokens``: 추가/제거 단어 list (TOP-N)
- ``signal``: ``"major"`` (sim < 0.5) / ``"moderate"`` (0.5~0.85) / ``"minor"`` (≥0.85)
"""

from __future__ import annotations

import re

import polars as pl

_RE_WORD = re.compile(r"[A-Za-z0-9_]{2,}")


def _tokenize(text: str) -> set[str]:
    """text → unique lowercase token set (≥ 2 char)."""
    if not text:
        return set()
    return {t.lower() for t in _RE_WORD.findall(text)}


def textSimilarity(left: str, right: str) -> float:
    """두 텍스트 Jaccard token similarity (0.0~1.0).

    Args:
        left: 첫 텍스트.
        right: 둘째 텍스트.

    Returns:
        ``|L ∩ R| / |L ∪ R|`` — 양쪽 빈 텍스트 → 1.0, 한쪽만 빈 → 0.0.

    Raises:
        없음.

    Example:
        >>> textSimilarity("revenue grew", "revenue grew strongly")
        0.6666666666666666
    """
    L = _tokenize(left)
    R = _tokenize(right)
    if not L and not R:
        return 1.0
    if not L or not R:
        return 0.0
    inter = L & R
    union = L | R
    return len(inter) / len(union)


def evaluateDiff(left: str, right: str, *, topN: int = 10) -> dict[str, object]:
    """두 텍스트 diff 정량 평가 — similarity + added/removed token TOP-N + signal.

    Args:
        left: 이전 period 텍스트.
        right: 현재 period 텍스트.
        topN: added/removed list 최대 길이.

    Returns:
        ``{"textSimilarity": float, "addedTokens": list[str],
        "removedTokens": list[str], "signal": "major"|"moderate"|"minor"}``.

    Raises:
        없음.

    Example:
        >>> result = evaluateDiff("revenue grew", "revenue declined")
        >>> result["signal"]
        'major'
    """
    L = _tokenize(left)
    R = _tokenize(right)
    sim = textSimilarity(left, right)
    added = sorted(R - L)[:topN]
    removed = sorted(L - R)[:topN]
    if sim < 0.5:
        signal = "major"
    elif sim < 0.85:
        signal = "moderate"
    else:
        signal = "minor"
    return {
        "textSimilarity": sim,
        "addedTokens": added,
        "removedTokens": removed,
        "signal": signal,
    }


def fetchDiffRows(pairs: list[tuple[str, str, str]], *, limit: int = 100) -> pl.DataFrame:
    """다중 (section, left, right) pair 배치 diff → DataFrame.

    Args:
        pairs: ``[(sectionName, leftText, rightText), ...]``.
        limit: 결과 최대 row 수.

    Returns:
        5 컬럼 DataFrame: ``section`` / ``textSimilarity`` / ``addedCount`` /
        ``removedCount`` / ``signal``.

    Raises:
        없음.

    Example:
        >>> df = fetchDiffRows([("MD&A", "old text", "new text")])  # doctest: +SKIP
    """
    if not pairs:
        return pl.DataFrame(
            schema={
                "section": pl.Utf8,
                "textSimilarity": pl.Float64,
                "addedCount": pl.Int64,
                "removedCount": pl.Int64,
                "signal": pl.Utf8,
            }
        )
    rows: list[dict[str, object]] = []
    for section, left, right in pairs[:limit] if limit > 0 else pairs:
        result = evaluateDiff(left, right)
        rows.append(
            {
                "section": section,
                "textSimilarity": result["textSimilarity"],
                "addedCount": len(result["addedTokens"]),
                "removedCount": len(result["removedTokens"]),
                "signal": result["signal"],
            }
        )
    return pl.DataFrame(rows)


def iterDiffRows(pairs: list[tuple[str, str, str]], *, batchSize: int = 20):
    """``fetchDiffRows`` 의 streaming pair (룰 10) — batchSize 단위 yield.

    Args:
        pairs: ``[(sectionName, leftText, rightText), ...]``.
        batchSize: batch 당 pair 수.

    Yields:
        pl.DataFrame — batch 단위 결과.

    Raises:
        없음.

    Example:
        >>> for batch in iterDiffRows(pairs):
        ...     pass  # doctest: +SKIP
    """
    n = len(pairs)
    for start in range(0, n, batchSize):
        yield fetchDiffRows(pairs[start : start + batchSize])
