"""DartLab AI public ask entry point.

본체는 `ai/agent.py` (runAgent — chat-native + LLM 자율 tool calling).
분석 의도 (mode="analyze" 또는 종목코드 / 분석 키워드) 시 `WorkbenchLoop` 5 패스 활성.

회귀 방지: memory/feedback_no_graph_regression.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .agent import runAgent
from .contracts import TraceEvent, WorkbenchTask
from .workbench import WorkbenchLoop
from .workbench.intent import isAnalysisIntent


def create_task(question: str, **_: Any) -> WorkbenchTask:
    """Create a compact research task for compatibility callers."""

    return WorkbenchTask(question=(question or "").strip())


def _ask_events(question: str, **kwargs: Any) -> Iterator[TraceEvent]:
    """Internal event stream for server/CLI adapters.

    Public callers should use :func:`ask`. agent_gateway 와 같은 분기 룰:
    - 명시적 mode="analyze" / 종목코드 / 분석 키워드 → WorkbenchLoop (5 패스)
    - 그 외 → runAgent (LLM 자율 tool calling)
    """
    mode = str(kwargs.get("mode") or kwargs.get("dialogueMode") or "").lower()
    use_workbench = mode in {"analyze", "analysis", "research", "workbench"} or isAnalysisIntent(question, kwargs)

    if use_workbench:
        yield from WorkbenchLoop().stream(question, **kwargs)
        return

    provider_obj = kwargs.pop("provider", None)
    if provider_obj is None:
        provider_obj = _resolveProvider(kwargs)
    if provider_obj is None or not _isLLMProvider(provider_obj):
        # provider 미해결 — workbench heuristic 으로 fallback (LLM 없이도 답)
        yield from WorkbenchLoop().stream(question, **kwargs)
        return

    yield from runAgent(question, provider=provider_obj, **kwargs)


def _resolveProvider(kwargs: dict[str, Any]) -> Any:
    try:
        from .providers import create_provider

        return create_provider(
            provider=kwargs.get("provider"),
            model=kwargs.get("model"),
        )
    except Exception:  # noqa: BLE001
        return None


def _isLLMProvider(obj: Any) -> bool:
    if obj is None or not callable(getattr(obj, "generate", None)):
        return False
    config = getattr(obj, "config", None)
    provider_id = (getattr(config, "provider", None) or "").lower()
    if provider_id not in {
        "oauth-codex",
        "openai",
        "gemini",
        "codex",
        "ollama",
        "custom",
        "groq",
        "cerebras",
        "mistral",
    }:
        return False
    try:
        return bool(obj.check_available())
    except Exception:  # noqa: BLE001
        return False


def ask(question: str, *, stream: bool = True, events: bool = False, **kwargs: Any):
    """Ask DartLab.

    ``stream=True`` returns text chunks. ``stream=False`` returns the complete
    text. ``events=True`` is reserved for DartLab adapters and returns internal
    TraceEvent objects without exposing a second public answer entry point.
    """

    event_iter = _ask_events(question, **kwargs)
    if events:
        return event_iter
    if stream:
        return _chunk_iter(event_iter)
    return "".join(event.data.get("text", "") for event in event_iter if event.kind == "chunk")


def _chunk_iter(events: Iterator[TraceEvent]) -> Iterator[str]:
    for event in events:
        if event.kind == "chunk":
            text = event.data.get("text", "")
            if text:
                yield str(text)


__all__ = ["ask", "create_task"]
