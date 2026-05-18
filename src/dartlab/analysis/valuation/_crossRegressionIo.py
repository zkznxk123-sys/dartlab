"""crossRegression 의 IO — saveModel/loadModel/savePanelModel/loadPanelModel."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dartlab.analysis.valuation._crossRegressionTypes import (
    CrossSectionModel,
    PanelModel,
)

log = logging.getLogger(__name__)

_MODEL_CACHE_DIR = Path.home() / ".dartlab" / "models"

FEATURES = [
    "per",
    "pbr",
    "lnMarketCap",
    "operatingMargin",
    "capexRatio",
    "debtRatio",
    "foreignHoldingRatio",
    "revenueGrowthLag",
]


def saveModel(model: CrossSectionModel) -> Path:
    """횡단면 모델 JSON 저장.

    Parameters
    ----------
    model : CrossSectionModel
        저장할 횡단면 회귀 모델.

    Returns
    -------
    Path
        저장된 파일 경로 (~/.dartlab/models/crossSection_{year}.json).

    Capabilities:
        - dataclass → JSON 직렬화 → 캐시 디렉토리 기록
        - 동일 연도 덮어쓰기

    Guide:
        일 1 회 사전 적합 후 캐시. loadModel 이 사용.

    When:
        모델 적합 후 디스크 저장.

    How:
        dict 변환 → json.dumps → Path.write_text.

    Requires:
        쓰기 권한 + ``~/.dartlab/models/``.

    Raises:
        없음.

    Example:
        >>> saveModel(model)
        PosixPath('/.../crossSection_2025.json')

    SeeAlso:
        - loadModel : 복원
        - fitCrossSection : 적합

    AIContext:
        사전 적합 모델 저장. AI 답변 시 invisible.
    """
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _MODEL_CACHE_DIR / f"crossSection_{model.year}.json"
    data = {
        "year": model.year,
        "coefficients": model.coefficients,
        "featureNames": model.featureNames,
        "rSquared": model.rSquared,
        "adjRSquared": model.adjRSquared,
        "nObs": model.nObs,
        "sectorNames": model.sectorNames,
        "warnings": model.warnings,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("CrossSection 모델 저장: %s (%d obs, R²=%.3f)", path, model.nObs, model.rSquared)
    return path


def loadModel(year: int) -> CrossSectionModel | None:
    """캐시된 횡단면 모델 로드.

    Parameters
    ----------
    year : int
        적합 연도.

    Returns
    -------
    CrossSectionModel | None
        캐시된 모델. 파일 없거나 파싱 실패 시 None.

    Capabilities:
        - 캐시 JSON → CrossSectionModel dataclass 복원
        - 파일 없거나 schema 불일치 시 None

    Guide:
        예측 시점 무거운 재적합 회피. None 시 fitCrossSection 재실행.

    When:
        예측 직전 캐시 hit 시도.

    How:
        Path.read_text → json.loads → dataclass(**data).

    Requires:
        ``crossSection_{year}.json`` 가용.

    Raises:
        없음 — 파싱 실패 시 None.

    Example:
        >>> loadModel(2025).rSquared
        0.32

    SeeAlso:
        - saveModel : 저장
        - fitCrossSection : 적합

    AIContext:
        AI 예측 호출 시 invisible cache.
    """
    path = _MODEL_CACHE_DIR / f"crossSection_{year}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CrossSectionModel(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        log.debug("CrossSection 모델 로드 실패: %s — %s", path, e)
        return None


def savePanelModel(model: PanelModel) -> Path:
    """패널 모델 JSON 저장.

    Parameters
    ----------
    model : PanelModel
        저장할 패널 회귀 모델.

    Returns
    -------
    Path
        저장된 파일 경로 (~/.dartlab/models/panel_latest.json).

    Capabilities:
        - PanelModel → JSON (firmIntercepts dict 포함) 저장
        - 1 개 파일만 유지 (latest)

    Guide:
        패널은 단일 latest 캐시. 새 적합 시 덮어쓰기.

    When:
        패널 모델 추정 후 캐싱.

    How:
        dict 변환 → write_text.

    Requires:
        쓰기 권한.

    Raises:
        없음.

    Example:
        >>> savePanelModel(panel)
        PosixPath('/.../panel_latest.json')

    SeeAlso:
        - loadPanelModel : 복원
        - fitPanel : 적합

    AIContext:
        패널 사전 적합 캐싱. AI invisible.
    """
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _MODEL_CACHE_DIR / "panel_latest.json"
    data = {
        "coefficients": model.coefficients,
        "featureNames": model.featureNames,
        "rSquared": model.rSquared,
        "nObs": model.nObs,
        "nFirms": model.nFirms,
        "firmIntercepts": model.firmIntercepts,
        "grandMean": model.grandMean,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Panel 모델 저장: %s (%d obs, %d firms)", path, model.nObs, model.nFirms)
    return path


def loadPanelModel() -> PanelModel | None:
    """캐시된 패널 모델 로드.

    Returns
    -------
    PanelModel | None
        캐시된 모델. 파일 없거나 파싱 실패 시 None.

    Capabilities:
        - panel_latest.json 캐시 → PanelModel 복원
        - 파일 없음 또는 schema 변경 시 None

    Guide:
        예측 직전 cache hit 시도. None 시 fitPanel 재실행.

    When:
        패널 예측 직전.

    How:
        read_text → json.loads → PanelModel(**data).

    Requires:
        ``panel_latest.json`` 가용.

    Raises:
        없음.

    Example:
        >>> loadPanelModel().nFirms
        320

    SeeAlso:
        - savePanelModel : 저장
        - fitPanel : 적합

    AIContext:
        AI invisible cache.
    """
    path = _MODEL_CACHE_DIR / "panel_latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PanelModel(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        log.debug("Panel 모델 로드 실패: %s — %s", path, e)
        return None


# ══════════════════════════════════════════════════════════
# 내부 유틸
# ══════════════════════════════════════════════════════════
