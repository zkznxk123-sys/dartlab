"""providers/dart/docs/finance/affiliate/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.affiliate.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_movements_callable() -> None:
    """extractMovements() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.parser import extractMovements

    assert callable(extractMovements)


def test_extract_profiles_callable() -> None:
    """extractProfiles() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.parser import extractProfiles

    assert callable(extractProfiles)


def test_extract_simple_movement_callable() -> None:
    """extractSimpleMovement() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.parser import extractSimpleMovement

    assert callable(extractSimpleMovement)


def test_extract_transposed_movements_callable() -> None:
    """extractTransposedMovements() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.parser import extractTransposedMovements

    assert callable(extractTransposedMovements)


def test_extract_transposed_profiles_callable() -> None:
    """extractTransposedProfiles() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.parser import extractTransposedProfiles

    assert callable(extractTransposedProfiles)
