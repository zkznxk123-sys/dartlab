"""edinet disclosure mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.edinet import disclosure

    assert disclosure.__all__ == []
