"""횡단면·패널 회귀 매출 예측 엔진 — facade. 본체는 `_crossRegressionTypes` / `_crossRegressionFit` / `_crossRegressionIo`.

횡단면 회귀: 같은 시점에 전 상장사 데이터를 모아 매출 성장률을 설명.
패널 회귀: 여러 연도를 쌓아 기업 고정효과(fixed effect)로 기업 특성 통제.

모든 구현은 순수 Python (외부 ML 라이브러리 의존 없음).
사전 적합(pre-fit) 후 JSON 캐시 → 개별 기업 예측은 즉시 계산.
"""

from __future__ import annotations

from dartlab.analysis.valuation._crossRegressionFit import (
    FEATURES,
    _winsorizeObs,
    fitCrossSection,
    fitPanel,
)
from dartlab.analysis.valuation._crossRegressionIo import (
    _MODEL_CACHE_DIR,
    loadModel,
    loadPanelModel,
    saveModel,
    savePanelModel,
)
from dartlab.analysis.valuation._crossRegressionTypes import (
    CompanyFeatures,
    CrossSectionModel,
    PanelModel,
)

__all__ = [
    "FEATURES",
    "CompanyFeatures",
    "CrossSectionModel",
    "PanelModel",
    "_MODEL_CACHE_DIR",
    "_winsorizeObs",
    "fitCrossSection",
    "fitPanel",
    "loadModel",
    "loadPanelModel",
    "saveModel",
    "savePanelModel",
]
