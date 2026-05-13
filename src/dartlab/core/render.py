"""Chart HTML renderer protocol and registry."""

from __future__ import annotations

import sys
from typing import Protocol, runtime_checkable


@runtime_checkable
class ChartHtmlRenderer(Protocol):
    """ChartSpec dict 를 HTML 문자열로 변환하는 renderer protocol."""

    def htmlFromSpec(self, spec: dict) -> str:
        """ChartSpec 를 HTML 문자열로 변환한다."""
        ...


_renderer: ChartHtmlRenderer | None = None


def register(renderer: ChartHtmlRenderer) -> None:
    """차트 렌더러를 등록한다. 후속 등록은 이전 등록을 덮어쓴다."""
    global _renderer
    _renderer = renderer


def getRenderer() -> ChartHtmlRenderer | None:
    """등록된 렌더러를 반환한다. 미등록이면 viz lazy load 를 한 번 시도한다."""
    global _renderer
    if _renderer is None:
        try:
            import importlib

            importlib.import_module("dartlab.viz")
        except ImportError:
            return None
    return _renderer


registry = sys.modules[__name__]
protocols = sys.modules[__name__]
sys.modules.setdefault(__name__ + ".registry", registry)
sys.modules.setdefault(__name__ + ".protocols", protocols)

__all__ = ["ChartHtmlRenderer", "getRenderer", "protocols", "register", "registry"]
