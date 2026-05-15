"""[shim] credit/models/merton → synth/distress/merton SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.distress.merton`` 로 이동 — Merton 구조 모형 (CHS·survival 과 함께).
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.distress.merton import solveMerton, calcEquityVolatility
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 synth/distress/merton 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.distress.merton")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.synth.distress.merton' has no attribute {name!r}") from exc
