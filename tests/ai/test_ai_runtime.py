"""AI runtime 재정비 후 남은 공식 런타임 계약 테스트."""

from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.unit


def test_legacy_ai_runtime_package_is_removed():
    assert importlib.util.find_spec("dartlab.ai.runtime") is None


def test_public_ask_non_stream_returns_text():
    import dartlab

    answer = dartlab.ask("너 뭐 할 수 있니", stream=False)

    assert isinstance(answer, str)
    assert answer.strip()


def test_public_ask_stream_returns_text_chunks():
    import dartlab

    chunks = list(dartlab.ask("너 뭐 할 수 있니", stream=True))

    assert chunks
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_internal_events_are_reserved_for_adapters():
    from dartlab.ai.kernel import ask

    events = list(ask("너 뭐 할 수 있니", events=True))

    assert events
    assert events[-1].kind == "done"
