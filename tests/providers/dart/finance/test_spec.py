"""providers/dart/finance/spec.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.finance.spec  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_spec_callable() -> None:
    """buildSpec() callable smoke."""
    from dartlab.providers.dart.finance.spec import buildSpec

    assert callable(buildSpec)
