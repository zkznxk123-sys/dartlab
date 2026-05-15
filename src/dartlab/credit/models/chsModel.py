"""[shim] credit/models/chsModel → synth/distress/chsModel SSOT.

본체는 ``dartlab.synth.distress.chsModel`` 로 이동 (L1.5 공통계산 인프라).
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.distress import calcCHS, CHSResult
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 synth/distress/chsModel 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.distress.chsModel")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.credit.models.chsModel' has no attribute {name!r}") from exc
