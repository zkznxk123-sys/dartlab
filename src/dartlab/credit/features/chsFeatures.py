"""[shim] credit/features/chsFeatures → synth/distress/chsFeatures SSOT.

본체는 ``dartlab.synth.distress.chsFeatures`` 로 이동 (L1.5 공통계산 인프라).
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.distress import extractChsFeatures, computeChsProbability
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 synth/distress/chsFeatures 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.distress.chsFeatures")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.credit.features.chsFeatures' has no attribute {name!r}") from exc
