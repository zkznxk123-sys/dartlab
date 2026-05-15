"""[shim] macro/rates/impliedERP → synth/impliedERP SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.impliedERP`` 로 이동.
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.impliedERP import calcImpliedERP
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 synth/impliedERP 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.impliedERP")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.macro.rates.impliedERP' has no attribute {name!r}") from exc
