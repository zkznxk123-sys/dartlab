"""providers/dart/report/extract.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.report.extract  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_annual_callable() -> None:
    """extractAnnual() callable smoke."""
    from dartlab.providers.dart.report.extract import extractAnnual

    assert callable(extractAnnual)


def test_extract_clean_callable() -> None:
    """extractClean() callable smoke."""
    from dartlab.providers.dart.report.extract import extractClean

    assert callable(extractClean)


def test_extract_raw_callable() -> None:
    """extractRaw() callable smoke."""
    from dartlab.providers.dart.report.extract import extractRaw

    assert callable(extractRaw)


def test_extract_result_callable() -> None:
    """extractResult() callable smoke."""
    from dartlab.providers.dart.report.extract import extractResult

    assert callable(extractResult)
