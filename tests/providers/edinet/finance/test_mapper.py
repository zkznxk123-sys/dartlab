"""providers/edinet/finance/mapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.finance.mapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_map_callable() -> None:
    """map() callable smoke."""
    from dartlab.providers.edinet.finance.mapper import EdinetMapper

    assert hasattr(EdinetMapper, "map")


def test_mapping_rate_callable() -> None:
    """mappingRate() callable smoke."""
    from dartlab.providers.edinet.finance.mapper import EdinetMapper

    assert hasattr(EdinetMapper, "mappingRate")
