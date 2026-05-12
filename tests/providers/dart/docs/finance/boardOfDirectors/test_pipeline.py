"""providers/dart/docs/finance/boardOfDirectors/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.boardOfDirectors.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_board_of_directors_callable() -> None:
    """boardOfDirectors() callable smoke."""
    from dartlab.providers.dart.docs.finance.boardOfDirectors.pipeline import boardOfDirectors

    assert callable(boardOfDirectors)
