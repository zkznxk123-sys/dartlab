"""providers/dart/docs/finance/notesDetail.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.notesDetail  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_table_df_callable() -> None:
    """buildTableDf() callable smoke."""
    from dartlab.providers.dart.docs.finance.notesDetail import buildTableDf

    assert callable(buildTableDf)


def test_notes_detail_callable() -> None:
    """notesDetail() callable smoke."""
    from dartlab.providers.dart.docs.finance.notesDetail import notesDetail

    assert callable(notesDetail)
