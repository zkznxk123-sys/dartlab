"""providers/dart/docs/finance/riskDerivative.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.riskDerivative  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_detect_unit_callable() -> None:
    """detectUnit() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import detectUnit

    assert callable(detectUnit)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import parseAmount

    assert callable(parseAmount)


def test_parse_derivative_contracts_callable() -> None:
    """parseDerivativeContracts() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import parseDerivativeContracts

    assert callable(parseDerivativeContracts)


def test_parse_fx_sensitivity_callable() -> None:
    """parseFxSensitivity() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import parseFxSensitivity

    assert callable(parseFxSensitivity)


def test_risk_derivative_callable() -> None:
    """riskDerivative() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import riskDerivative

    assert callable(riskDerivative)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.riskDerivative import splitCells

    assert callable(splitCells)
