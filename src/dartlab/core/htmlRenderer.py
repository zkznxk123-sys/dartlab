"""Jupyter/Marimo HTML 렌더러 추상화 — DIP (정공법 B).

analysis 의 dataclass (RatioResult · InsightResult · DistressResult · AnalysisResult) 의
__repr__/_repr_html_ 가 viz/display 의 함수 (renderRatio · renderInsight · htmlDistress ·
htmlInsight) 를 lazy import 호출 → analysis ↔ viz 양방향 cycle 의 한 축.

HtmlRenderer Protocol 을 core 에 두고 viz/display 가 register. analysis 는 core import 만 —
viz 직접 의존 0. 미등록/렌더 실패 시 호출자가 fallback (repr 또는 <pre>).

CredentialProvider/LoaderProvider/ListingResolver/DisclosureFetcher/FinanceDocAccessor 와
동일 패턴.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HtmlRenderer(Protocol):
    """analysis dataclass → 텍스트/HTML 렌더 추상화 — analysis 가 사용."""

    def renderRatio(self, result: Any) -> str | None:
        """RatioResult → rich 텍스트. 실패 시 None."""
        ...

    def renderInsight(self, result: Any) -> str | None:
        """AnalysisResult → rich 텍스트. 실패 시 None."""
        ...

    def htmlDistress(self, result: Any) -> str | None:
        """DistressResult → HTML. 실패 시 None."""
        ...

    def htmlInsight(self, result: Any) -> str | None:
        """AnalysisResult → HTML. 실패 시 None."""
        ...


_RENDERER: HtmlRenderer | None = None

_KNOWN_RENDERER_MODULES: tuple[str, ...] = ("dartlab.viz.display.htmlRenderer",)
_DISCOVERED = False


def _discover() -> None:
    """알려진 HtmlRenderer 모듈을 한 번만 lazy import — register 트리거."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_RENDERER_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue
    _DISCOVERED = True


def registerHtmlRenderer(renderer: HtmlRenderer) -> None:
    """HtmlRenderer 등록 — viz/display 가 import 시점에 호출."""
    global _RENDERER
    _RENDERER = renderer


def getHtmlRenderer() -> HtmlRenderer | None:
    """현재 등록된 HtmlRenderer 반환. 미등록이면 None. auto-discovery 트리거."""
    _discover()
    return _RENDERER
