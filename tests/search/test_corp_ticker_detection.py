"""Search corp argument ticker detection tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_korean_short_company_name_is_not_us_ticker() -> None:
    from dartlab.providers.dart.search.api import _looksLikeUsTicker

    assert _looksLikeUsTicker("삼성전자") is False
    assert _looksLikeUsTicker("카카오") is False


def test_ascii_short_symbol_is_us_ticker() -> None:
    from dartlab.providers.dart.search.api import _looksLikeUsTicker

    assert _looksLikeUsTicker("AAPL") is True
    assert _looksLikeUsTicker("BRK.B") is True
    assert _looksLikeUsTicker("005930") is False
