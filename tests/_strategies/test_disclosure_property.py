"""core/disclosureFetcher hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


class _DummyFetcher:
    """test fixture — protocol satisfier."""

    def __init__(self, marker: str = "stub") -> None:
        self.marker = marker

    def fetch(self, stockCode: str, *, days: int = 400, type: str = "A") -> None:
        return None


@pytest.mark.unit
class TestDisclosureFetcherProperty:
    """disclosureFetcher 등록·조회 property 4."""

    def test_register_get_round_trip(self) -> None:
        from dartlab.core.disclosureFetcher import (
            getDisclosureFetcher,
            registerDisclosureFetcher,
        )

        prior = getDisclosureFetcher()
        try:
            f = _DummyFetcher(marker="test")
            registerDisclosureFetcher(f)
            got = getDisclosureFetcher()
            assert got is f
        finally:
            registerDisclosureFetcher(prior) if prior else None

    @given(marker=st.text(min_size=1, max_size=10))
    def test_register_overrides(self, marker: str) -> None:
        from dartlab.core.disclosureFetcher import (
            getDisclosureFetcher,
            registerDisclosureFetcher,
        )

        prior = getDisclosureFetcher()
        try:
            f = _DummyFetcher(marker=marker)
            registerDisclosureFetcher(f)
            assert getDisclosureFetcher().marker == marker
        finally:
            registerDisclosureFetcher(prior) if prior else None

    def test_protocol_runtime_check(self) -> None:
        from dartlab.core.disclosureFetcher import DisclosureFetcher

        assert isinstance(_DummyFetcher(), DisclosureFetcher)

    def test_non_fetcher_fails_protocol(self) -> None:
        from dartlab.core.disclosureFetcher import DisclosureFetcher

        class _NotFetcher:
            pass

        assert not isinstance(_NotFetcher(), DisclosureFetcher)
