"""gather/edgar/batch.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.batch  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_batch_collect_edgar_callable() -> None:
    """batchCollectEdgar() callable smoke."""
    from dartlab.gather.edgar.batch import batchCollectEdgar

    assert callable(batchCollectEdgar)


def test_batch_collect_edgar_all_callable() -> None:
    """batchCollectEdgarAll() callable smoke."""
    from dartlab.gather.edgar.batch import batchCollectEdgarAll

    assert callable(batchCollectEdgarAll)
