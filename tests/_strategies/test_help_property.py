"""dartlab.help hypothesis property — T6-1."""

from __future__ import annotations

import importlib

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestHelpProperty:
    """help() 검색 함수 property 5."""

    def test_empty_query_returns_results(self) -> None:
        hmod = importlib.import_module("dartlab.help")
        results = hmod.help("", limit=3)
        assert isinstance(results, list)
        assert len(results) <= 3

    @given(limit=st.integers(min_value=1, max_value=20))
    def test_limit_respected(self, limit: int) -> None:
        hmod = importlib.import_module("dartlab.help")
        results = hmod.help("show", limit=limit)
        assert len(results) <= limit

    @given(query=st.text(min_size=1, max_size=20))
    def test_score_in_range(self, query: str) -> None:
        hmod = importlib.import_module("dartlab.help")
        for r in hmod.help(query, limit=5):
            assert 0.0 <= r.score <= 1.0

    @given(query=st.text(min_size=1, max_size=20))
    def test_results_sorted_desc(self, query: str) -> None:
        hmod = importlib.import_module("dartlab.help")
        scores = [r.score for r in hmod.help(query, limit=10)]
        assert scores == sorted(scores, reverse=True)

    def test_helpresult_has_required_fields(self) -> None:
        hmod = importlib.import_module("dartlab.help")
        results = hmod.help("", limit=1)
        if results:
            r = results[0]
            assert hasattr(r, "name")
            assert hasattr(r, "kind")
            assert hasattr(r, "score")
