"""[shim] quant/risk/bottomUpBeta → synth/bottomUpBeta SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.bottomUpBeta`` 로 이동 — Damodaran Hamada unlever/relever.
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.bottomUpBeta import calcBottomUpBeta
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 synth/bottomUpBeta 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.bottomUpBeta")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.quant.risk.bottomUpBeta' has no attribute {name!r}") from exc
