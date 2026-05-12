"""providers/dart/openapi/saver.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.saver  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_enrich_finance_callable() -> None:
    """enrichFinance() callable smoke."""
    from dartlab.providers.dart.openapi.saver import enrichFinance

    assert callable(enrichFinance)


def test_enrich_report_callable() -> None:
    """enrichReport() callable smoke."""
    from dartlab.providers.dart.openapi.saver import enrichReport

    assert callable(enrichReport)


def test_kor_columns_callable() -> None:
    """korColumns() callable smoke."""
    from dartlab.providers.dart.openapi.saver import korColumns

    assert callable(korColumns)


def test_save_callable() -> None:
    """save() callable smoke."""
    from dartlab.providers.dart.openapi.saver import save

    assert callable(save)
