"""providers/dart/docs/viewer.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.viewer  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_serialize_viewer_block_callable() -> None:
    """serializeViewerBlock() callable smoke."""
    from dartlab.providers.dart.docs.viewer import serializeViewerBlock

    assert callable(serializeViewerBlock)


def test_serialize_viewer_text_document_callable() -> None:
    """serializeViewerTextDocument() callable smoke."""
    from dartlab.providers.dart.docs.viewer import serializeViewerTextDocument

    assert callable(serializeViewerTextDocument)


def test_viewer_blocks_callable() -> None:
    """viewerBlocks() callable smoke."""
    from dartlab.providers.dart.docs.viewer import viewerBlocks

    assert callable(viewerBlocks)


def test_viewer_text_document_callable() -> None:
    """viewerTextDocument() callable smoke."""
    from dartlab.providers.dart.docs.viewer import viewerTextDocument

    assert callable(viewerTextDocument)
