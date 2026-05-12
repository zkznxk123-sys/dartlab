"""providers/dart/docs/tableAI.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.tableAI  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_raw_markdown_block_callable() -> None:
    """parseRawMarkdownBlock() callable smoke."""
    from dartlab.providers.dart.docs.tableAI import parseRawMarkdownBlock

    assert callable(parseRawMarkdownBlock)
