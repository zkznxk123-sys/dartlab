"""[shim] credit/models/excessBondPremium → macro/crisis/excessBondPremium SSOT.

본체는 ``dartlab.macro.crisis.excessBondPremium`` 로 이동 (Gilchrist-Zakrajšek EBP).
본 모듈은 BC 만 유지. 신규 코드는 macro 본체 직접 호출:

    from dartlab.macro.crisis.excessBondPremium import approximateEBP, classifyEBP
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 macro/crisis/excessBondPremium 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.macro.crisis.excessBondPremium")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.credit.models.excessBondPremium' has no attribute {name!r}") from exc
