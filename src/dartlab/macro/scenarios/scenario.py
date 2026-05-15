"""[shim] macro/scenarios/scenario → synth/scenario SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.scenario`` 로 이동 — 시나리오 타입·업종 감응도·노이즈 SSOT.
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.scenario import (
        MacroScenario, SectorElasticity, getElasticity,
        BASELINE_FX, BASELINE_RATE, DEFAULT_ELASTICITY,
    )
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 synth/scenario 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.scenario")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.macro.scenarios.scenario' has no attribute {name!r}") from exc
