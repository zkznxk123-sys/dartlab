"""unified 모듈 mirror smoke — searchUnified 공개 표면."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.search import unified

    assert unified is not None


def test_search_unified_callable() -> None:
    """searchUnified() callable smoke."""
    from dartlab.providers.dart.search.unified import searchUnified

    assert callable(searchUnified)


def test_empty_query_returns_empty() -> None:
    """빈 질의 → 빈 DataFrame (인덱스 접근 0)."""
    import polars as pl

    from dartlab.providers.dart.search.unified import searchUnified

    df = searchUnified("")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 0
