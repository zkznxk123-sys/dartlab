"""[shim] credit/monitoring/crisisDetector → macro/crisis/detectors SSOT.

본체는 ``dartlab.macro.crisis.detectors`` 로 이동 (매크로 위기 지표 도메인).
본 모듈은 BC 만 유지. 신규 코드는 macro 본체 직접 호출:

    from dartlab.macro.crisis.detectors import (
        creditToGDPGap, ghsCrisisScore, recessionDashboard,
        minskyPhase, kooBalanceSheetRecession, fisherDebtDeflation,
        krHousingFinancialStress, dalioDebtCyclePhase, dalioPolicyLeverStatus,
    )
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 macro/crisis/detectors 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.macro.crisis.detectors")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.credit.monitoring.crisisDetector' has no attribute {name!r}") from exc
