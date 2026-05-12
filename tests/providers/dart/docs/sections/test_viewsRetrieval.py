"""viewsRetrieval.py mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.docs.sections import viewsRetrieval

    assert hasattr(viewsRetrieval, "retrievalBlocks")


def test_retrieval_blocks_callable() -> None:
    """retrievalBlocks() callable smoke."""
    from dartlab.providers.dart.docs.sections.viewsRetrieval import retrievalBlocks

    assert callable(retrievalBlocks)
