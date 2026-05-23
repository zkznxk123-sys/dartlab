"""edgar/parse/tableHorizontalizer test — iXBRL fact long → wide pivot."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_horizontalize_empty() -> None:
    """빈 DataFrame → 빈."""
    from dartlab.providers.edgar.parse import horizontalizeFacts

    df = pl.DataFrame(schema={"concept": pl.Utf8, "value": pl.Utf8, "contextRef": pl.Utf8})
    result = horizontalizeFacts(df)
    assert result.is_empty()


def test_horizontalize_missing_columns() -> None:
    """필수 컬럼 부재 → 빈."""
    from dartlab.providers.edgar.parse import horizontalizeFacts

    df = pl.DataFrame({"foo": [1, 2]})
    result = horizontalizeFacts(df)
    assert result.is_empty()


def test_horizontalize_basic() -> None:
    """concept × context wide pivot."""
    from dartlab.providers.edgar.parse import horizontalizeFacts

    facts = pl.DataFrame(
        {
            "concept": ["Revenue", "Revenue", "Assets", "Assets"],
            "contextRef": ["FY24", "FY23", "FY24", "FY23"],
            "value": ["100", "90", "500", "450"],
        }
    )
    wide = horizontalizeFacts(facts)
    assert wide.shape[0] == 2
    assert "FY24" in wide.columns
    assert "FY23" in wide.columns


def test_fetch_slice_concept_filter() -> None:
    """concept 필터 + horizontalize 통합."""
    from dartlab.providers.edgar.parse import fetchHorizontalSlice

    facts = pl.DataFrame(
        {
            "concept": ["Revenue", "Revenue", "Assets", "Assets"],
            "contextRef": ["FY24", "FY23", "FY24", "FY23"],
            "value": ["100", "90", "500", "450"],
        }
    )
    rev = fetchHorizontalSlice(facts, ["Revenue"])
    assert rev.shape[0] == 1
    assert rev["concept"][0] == "Revenue"


def test_iter_pair() -> None:
    """fetchHorizontalSlice ↔ iterHorizontalSlice 시그니처 (룰 10)."""
    import inspect

    from dartlab.providers.edgar.parse import fetchHorizontalSlice, iterHorizontalSlice

    assert "facts" in inspect.signature(fetchHorizontalSlice).parameters
    assert "concepts" in inspect.signature(fetchHorizontalSlice).parameters
    assert "facts" in inspect.signature(iterHorizontalSlice).parameters
    assert "conceptGroups" in inspect.signature(iterHorizontalSlice).parameters
