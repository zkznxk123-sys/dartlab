"""gather/edgar/saver.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.saver  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_save_docs_callable() -> None:
    """saveDocs() callable smoke."""
    from dartlab.gather.edgar.saver import saveDocs

    assert callable(saveDocs)


def test_save_finance_callable() -> None:
    """saveFinance() callable smoke."""
    from dartlab.gather.edgar.saver import saveFinance

    assert callable(saveFinance)


def test_verify_open_edgar_save_compatibility_callable() -> None:
    """verifyOpenEdgarSaveCompatibility() callable smoke."""
    from dartlab.gather.edgar.saver import verifyOpenEdgarSaveCompatibility

    assert callable(verifyOpenEdgarSaveCompatibility)
