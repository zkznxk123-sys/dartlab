"""[shim] macro/rates/riskPremiums → synth/riskPremiums SSOT (L1.5 공통계산 인프라).

본체는 ``dartlab.synth.riskPremiums`` 로 이동 — 도메인 중립 Damodaran ERP SSOT.
본 모듈은 BC 만 유지. 신규 코드는 synth 본체 직접 호출:

    from dartlab.synth.riskPremiums import loadDamodaranERP
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 synth/riskPremiums 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.synth.riskPremiums")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.macro.rates.riskPremiums' has no attribute {name!r}") from exc
