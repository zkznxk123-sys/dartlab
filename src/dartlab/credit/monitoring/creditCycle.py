"""[shim] credit/monitoring/creditCycle → macro/crisis/creditCycleDetect SSOT.

본체는 ``dartlab.macro.crisis.creditCycleDetect`` 로 이동.
본 모듈은 BC 만 유지. 신규 코드는 macro 본체 직접 호출:

    from dartlab.macro.crisis.creditCycleDetect import classifyCreditCycle
"""

from __future__ import annotations


def __getattr__(name: str):
    """BC — 사용 시점에 macro/crisis/creditCycleDetect 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.macro.crisis.creditCycleDetect")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.credit.monitoring.creditCycle' has no attribute {name!r}") from exc
