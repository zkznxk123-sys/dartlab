"""DartLab AI public ask entry point."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .contracts import TraceEvent, WorkbenchTask
from .research_graph import DartLabResearchGraph


def create_task(question: str, **_: Any) -> WorkbenchTask:
    """Create a compact research task for compatibility callers."""

    return WorkbenchTask(question=(question or "").strip())


def _ask_events(question: str, **kwargs: Any) -> Iterator[TraceEvent]:
    """Internal event stream for server/CLI adapters.

    Public callers should use :func:`ask`.  This function exists so adapters can
    consume trace events without exposing a second answer entry point.
    """

    yield from DartLabResearchGraph().stream(question, **kwargs)


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
