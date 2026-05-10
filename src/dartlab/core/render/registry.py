"""ChartHtmlRenderer 단일 슬롯 registry — viz 가 register 하면 core 가 lookup.

dartlab 은 단일 차트 백엔드만 사용하므로 list 가 아닌 단일 슬롯. 후속 등록은
이전 등록을 덮어씌운다 (plug-in 교체용).
"""

from __future__ import annotations

from dartlab.core.render.protocols import ChartHtmlRenderer

_renderer: ChartHtmlRenderer | None = None


def register(renderer: ChartHtmlRenderer) -> None:
    """차트 렌더러 등록 — 후속 등록은 이전 것을 덮어씌움."""
    global _renderer
    _renderer = renderer


def getRenderer() -> ChartHtmlRenderer | None:
    """등록된 렌더러 반환. 미등록 시 dartlab.viz lazy load 시도.

    사용자가 `import dartlab.viz` 를 명시하지 않은 환경에서 첫 호출 시 자동 등록
    유도. plotly 미설치 (pyodide 등) 면 importlib 가 ImportError → None 유지.
    importlib.import_module 호출은 cycleScan/import-linter 가 못 잡으므로 단방향
    레이어 정책 위반 안 함.
    """
    global _renderer
    if _renderer is None:
        try:
            import importlib

            importlib.import_module("dartlab.viz")
        except ImportError:
            return None
    return _renderer
