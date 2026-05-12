"""providers/dart/docs/finance/majorHolder/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.majorHolder.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_holder_overview_callable() -> None:
    """holderOverview() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.pipeline import holderOverview

    assert callable(holderOverview)


def test_major_holder_callable() -> None:
    """majorHolder() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.pipeline import majorHolder

    assert callable(majorHolder)
