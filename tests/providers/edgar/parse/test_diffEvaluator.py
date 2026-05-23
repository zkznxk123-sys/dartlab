"""edgar/parse/diffEvaluator test — text similarity + diff signal 검증."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_text_similarity_identical() -> None:
    """동일 텍스트 → 1.0."""
    from dartlab.providers.edgar.parse import textSimilarity

    assert textSimilarity("revenue grew strongly", "revenue grew strongly") == 1.0


def test_text_similarity_disjoint() -> None:
    """공통 token 0 → 0.0."""
    from dartlab.providers.edgar.parse import textSimilarity

    sim = textSimilarity("foo bar baz", "alpha beta gamma")
    assert sim == 0.0


def test_text_similarity_both_empty() -> None:
    """양쪽 빈 → 1.0 (편의)."""
    from dartlab.providers.edgar.parse import textSimilarity

    assert textSimilarity("", "") == 1.0


def test_text_similarity_one_empty() -> None:
    """한쪽 빈 → 0.0."""
    from dartlab.providers.edgar.parse import textSimilarity

    assert textSimilarity("text", "") == 0.0
    assert textSimilarity("", "text") == 0.0


def test_evaluate_diff_signals() -> None:
    """sim 임계 → signal 분류 (major < 0.5, moderate 0.5~0.85, minor ≥0.85)."""
    from dartlab.providers.edgar.parse import evaluateDiff

    # 완전 다른 → major
    assert evaluateDiff("alpha beta", "gamma delta")["signal"] == "major"
    # 동일 → minor
    assert evaluateDiff("revenue grew", "revenue grew")["signal"] == "minor"


def test_evaluate_diff_added_removed() -> None:
    """addedTokens / removedTokens 분리."""
    from dartlab.providers.edgar.parse import evaluateDiff

    result = evaluateDiff("revenue grew strongly", "revenue declined slowly")
    assert "declined" in result["addedTokens"]
    assert "slowly" in result["addedTokens"]
    assert "grew" in result["removedTokens"]
    assert "strongly" in result["removedTokens"]


def test_fetch_diff_rows() -> None:
    """다중 pair batch diff DataFrame."""
    from dartlab.providers.edgar.parse import fetchDiffRows

    pairs = [
        ("MD&A", "revenue grew", "revenue grew strongly"),
        ("Risk", "alpha beta", "gamma delta"),
    ]
    df = fetchDiffRows(pairs)
    assert df.shape[0] == 2
    assert set(df.columns) >= {"section", "textSimilarity", "signal"}


def test_iter_pair() -> None:
    """fetchDiffRows ↔ iterDiffRows 일관성 (룰 10)."""
    import inspect

    from dartlab.providers.edgar.parse import fetchDiffRows, iterDiffRows

    assert "pairs" in inspect.signature(fetchDiffRows).parameters
    assert "limit" in inspect.signature(fetchDiffRows).parameters
    assert "pairs" in inspect.signature(iterDiffRows).parameters
    assert "batchSize" in inspect.signature(iterDiffRows).parameters
