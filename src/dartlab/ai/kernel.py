"""DartLab AI public ask entry point.

본체는 `ai/agent.py` (runAgent — chat-native + 모델 자율 tool calling).
5 패스 작업대 활성 경로 2 가지 (feedback_no_graph_regression.md SSOT):
1. 사용자 명시 `mode="analyze"` / `mode="workbench"`
2. 모델이 자율적으로 `run_workbench` 도구 호출 (agent.runAgent 안에서)

intent regex / 키워드 routing 폐기 (P-revised). 종목코드 자동 추출 / 분석 키워드 매치로
암묵적 elevate 안 한다.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .agent import runAgent
from .contracts import TraceEvent, WorkbenchTask
from .settings.providerCatalog import wiredProviderIds
from .workbench import WorkbenchLoop


def createTask(question: str, **_: Any) -> WorkbenchTask:
    """Create a compact research task for compatibility callers."""

    return WorkbenchTask(question=(question or "").strip())


def _askEvents(question: str, **kwargs: Any) -> Iterator[TraceEvent]:
    """Internal event stream for server/CLI adapters.

    분기 룰:
    - 명시적 `mode="analyze" / "workbench"` → WorkbenchLoop (5 패스)
    - 그 외 → runAgent (chat-native 자율 tool calling). 모델이 깊은 분석 필요 판단 시
      `run_workbench` 도구를 자율 호출 — agent.py 안에서 처리.
    """
    mode = str(kwargs.get("mode") or kwargs.get("dialogueMode") or "").lower()
    use_workbench = mode in {"analyze", "analysis", "research", "workbench"}

    if use_workbench:
        yield from WorkbenchLoop().stream(question, **kwargs)
        return

    provider_obj = kwargs.pop("provider", None)
    if provider_obj is None:
        provider_obj = _resolveProvider(kwargs)
    if provider_obj is None or not _isLLMProvider(provider_obj):
        # provider 미해결 — workbench heuristic 으로 fallback (모델 없이도 답).
        yield from WorkbenchLoop().stream(question, **kwargs)
        return

    yield from runAgent(question, provider=provider_obj, **kwargs)


def _resolveProvider(kwargs: dict[str, Any]) -> Any:
    try:
        from .providers import createProvider

        return createProvider(
            provider=kwargs.get("provider"),
            model=kwargs.get("model"),
        )
    except Exception:  # noqa: BLE001
        return None


def _isLLMProvider(obj: Any) -> bool:
    if obj is None or not callable(getattr(obj, "generate", None)):
        return False
    config = getattr(obj, "config", None)
    providerId = (getattr(config, "provider", None) or "").lower()
    if providerId not in wiredProviderIds():
        return False
    try:
        return bool(obj.checkAvailable())
    except Exception:  # noqa: BLE001
        return False


def ask(question: str, *, stream: bool = True, events: bool = False, **kwargs: Any):
    """Ask DartLab.

    ``stream=True`` returns text chunks. ``stream=False`` returns the complete
    text. ``events=True`` is reserved for DartLab adapters and returns internal
    TraceEvent objects without exposing a second public answer entry point.
    """

    event_iter = _askEvents(question, **kwargs)
    if events:
        return event_iter
    if stream:
        return _chunkIter(event_iter)
    return "".join(event.data.get("text", "") for event in event_iter if event.kind == "chunk")


def _chunkIter(events: Iterator[TraceEvent]) -> Iterator[str]:
    for event in events:
        if event.kind == "chunk":
            text = event.data.get("text", "")
            if text:
                yield str(text)


__all__ = ["ask", "createTask"]
