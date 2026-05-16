"""[shim] macro/cycles/turningPoint → synth/turningPoint SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.turningPoint`` 로 이동 — CUSUM + Rolling Z 도메인 중립.
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.turningPoint import detectTurningPoints, injectTurningPoints
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 synth/turningPoint 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.turningPoint")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.macro.cycles.turningPoint' has no attribute {name!r}") from exc
