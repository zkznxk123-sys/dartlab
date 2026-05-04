"""DartLab research graph compatibility boundary.

The production loop lives in :mod:`dartlab.ai.workbench`.  This wrapper keeps a
small graph-shaped object for server/CLI/tests without reintroducing helper
calls or provider state.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .contracts import TraceEvent
from .workbench import GRAPH_NODES, WorkbenchLoop


class DartLabResearchGraph:
    """Ask Workbench graph facade."""

    nodes = GRAPH_NODES

    def __init__(self) -> None:
        self._loop = WorkbenchLoop()

    def stream(self, question: str, **kwargs: Any) -> Iterator[TraceEvent]:
        yield from self._loop.stream(question, **kwargs)
