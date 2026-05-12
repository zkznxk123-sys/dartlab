"""providers/edgar/docs/sections/runtime.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.sections.runtime  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_fallback_topic_callable() -> None:
    """fallbackTopic() callable smoke."""
    from dartlab.providers.edgar.docs.sections.runtime import fallbackTopic

    assert callable(fallbackTopic)


def test_topic_namespace_callable() -> None:
    """topicNamespace() callable smoke."""
    from dartlab.providers.edgar.docs.sections.runtime import topicNamespace

    assert callable(topicNamespace)
