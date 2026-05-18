"""경기국면 전환 모델 — facade. 본체는 `_regimeSwitchingLei` / `_regimeSwitchingHamilton`.

Hamilton RS + Cleveland Fed 프로빗 + Conference Board LEI + Sahm Rule.
순수 데이터 + 판정 함수. numpy만 사용, 외부 통계 라이브러리 없음.
core/ 계층 소속 — macro(시장 해석) 엔진에서 소비.

학술 근거:
- Hamilton (1989): "A New Approach to the Economic Analysis of Nonstationary Time Series"
- Kim (1994): Smoother for Markov-Switching models
- Estrella & Mishkin (1996): Yield curve → recession probability
- Cleveland Fed: Yield Curve and Predicted GDP Growth model
- Conference Board: Leading Economic Index methodology
- Sahm (2019): Real-time unemployment recession indicator
"""

from __future__ import annotations

from dartlab.macro.cycles._regimeSwitchingHamilton import (
    HamiltonResult,
    _ergodicProbs,
    _gaussianDensity,
    _hamiltonFilter,
    _kimSmoother,
    hamiltonRegime,
)
from dartlab.macro.cycles._regimeSwitchingLei import (
    LEIResult,
    RecessionProb,
    SahmResult,
    _normalCdf,
    clevelandProbit,
    conferenceBoardLEI,
    sahmRule,
)

__all__ = [
    "HamiltonResult",
    "LEIResult",
    "RecessionProb",
    "SahmResult",
    "_ergodicProbs",
    "_gaussianDensity",
    "_hamiltonFilter",
    "_kimSmoother",
    "_normalCdf",
    "clevelandProbit",
    "conferenceBoardLEI",
    "hamiltonRegime",
    "sahmRule",
]
