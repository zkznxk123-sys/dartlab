"""[shim] quant/regime/quadrant → synth/quadrant SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.quadrant`` 로 이동. 본 모듈은 BC (backwards compat) 만 유지.
신규 코드는 ``from dartlab.synth.quadrant import classifyQuadrant`` 직접 호출.
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 synth/quadrant 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.quadrant")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.quant.regime.quadrant' has no attribute {name!r}") from exc
