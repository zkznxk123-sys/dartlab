"""agent 모듈 테스트 — reflection."""

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.runtime.agent import _reflect_on_answer
from dartlab.ai.types import ToolResponse


# ══════════════════════════════════════
# Reflection
# ══════════════════════════════════════


class MockProvider:
    """테스트용 mock LLM provider."""

    def __init__(self, answer: str):
        self._answer = answer

    def complete(self, messages):
        return ToolResponse(
            answer=self._answer,
            provider="mock",
            model="mock-1",
            tool_calls=[],
            finish_reason="stop",
        )


class TestReflection:
    def test_reflect_returns_improved(self):
        """reflection이 개선된 답변을 반환."""
        provider = MockProvider("개선된 답변입니다.")
        result = _reflect_on_answer(
            provider,
            [{"role": "user", "content": "질문"}],
            "원본 답변",
        )
        assert result == "개선된 답변입니다."

    def test_reflect_empty_keeps_original(self):
        """reflection이 비어있으면 원본 유지."""
        provider = MockProvider("  ")
        result = _reflect_on_answer(
            provider,
            [{"role": "user", "content": "질문"}],
            "원본 답변",
        )
        assert result == "원본 답변"
