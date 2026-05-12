"""providers/dart/docs/finance/segment/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.segment.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_segments_callable() -> None:
    """segments() callable smoke."""
    from dartlab.providers.dart.docs.finance.segment.pipeline import segments

    assert callable(segments)
