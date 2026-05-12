"""providers/dart/finance/sceMapper.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.finance.sceMapper  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_normalize_cause_callable() -> None:
    """normalizeCause() callable smoke."""
    from dartlab.providers.dart.finance.sceMapper import normalizeCause

    assert callable(normalizeCause)


def test_normalize_detail_callable() -> None:
    """normalizeDetail() callable smoke."""
    from dartlab.providers.dart.finance.sceMapper import normalizeDetail

    assert callable(normalizeDetail)
