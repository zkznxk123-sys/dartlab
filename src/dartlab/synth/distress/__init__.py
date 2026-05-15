"""L1.5 synth/distress — 부도 위험 모델 SSOT.

Campbell-Hilscher-Szilagyi (CHS) 12M PD + Damodaran survival weight.
credit ↔ analysis 양쪽 엔진이 동일 경로로 호출하는 중립 SSOT.

진입점:
    from dartlab.synth.distress import (
        calcCHS, CHSResult,
        extractChsFeatures, computeChsProbability,
        calcSurvivalWeight, applySurvivalWeight,
    )
"""

from __future__ import annotations

from dartlab.synth.distress.chsFeatures import computeChsProbability, extractChsFeatures
from dartlab.synth.distress.chsModel import CHSResult, calcCHS
from dartlab.synth.distress.survival import applySurvivalWeight, calcSurvivalWeight

__all__ = [
    "CHSResult",
    "applySurvivalWeight",
    "calcCHS",
    "calcSurvivalWeight",
    "computeChsProbability",
    "extractChsFeatures",
]
