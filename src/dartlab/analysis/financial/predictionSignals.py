"""6-2 예측신호 -- 이 회사의 실적은 어디로 향하는가.

다중 소스 예측 신호를 구조화된 데이터로 제공한다.
forecast 엔진(점 추정)과 달리, 방향성과 신뢰도에 집중한다.

학술 근거:
- Sloan 1996: 현금흐름 구성요소가 발생액보다 지속성 높음
- Cao & You 2024 (G&D Award): 횡단면 재무비율 → ML 이익 예측
- M Competition: 단순 앙상블이 복잡한 가중치를 이김
- M6: 방향 정확도가 점 정확도보다 투자에 유의미
"""

from __future__ import annotations

from dartlab.core.utils.safe import get as _get

_getF = _getF2 = _getF3 = _getF4 = _get

import logging
import math

from dartlab.analysis.financial._predictionMath import (
    _calcLagCorrelation,
    _fitOLS,
    _invertMatrix,
    _pearsonCorrelation,
    _quickCorr,
)
from dartlab.analysis.financial._predictionUtils import (
    _DIRECTION_SCORES,
    _bayesUpdate,
    _calibrate,
    _clamp,
)
from dartlab.core.financeDocAccessor import getFinanceDocAccessor
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

log = logging.getLogger(__name__)

_MAX_YEARS = 8

# ── 업종별 모멘텀 사전확률 + 매크로 매핑 (JSON 단일 진실의 원천) ──
import json
from pathlib import Path as _Path

_SECTOR_DATA = json.loads(
    (_Path(__file__).resolve().parents[2] / "providers" / "data" / "parserMappings" / "sectorPriors.json").read_text(
        encoding="utf-8"
    )
)
_INDUSTRY_PRIOR: dict[str, float] = _SECTOR_DATA.get("priors", {})
_DEFAULT_PRIOR: float = _SECTOR_DATA.get("_metadata", {}).get("defaultPrior", 0.721)
_SECTOR_MACRO_MAP: dict[str, list[dict]] = _SECTOR_DATA.get("sectorMacroMap", {})
_sensitivity = _SECTOR_DATA.get("sectorSensitivity", {})
_RATE_SENSITIVE_SECTORS = set(_sensitivity.get("rate", []))
_FX_SENSITIVE_SECTORS = set(_sensitivity.get("fx", []))
_COMMODITY_SECTORS = set(_sensitivity.get("commodity", []))


# ── 공통 헬퍼 ──


from dartlab.analysis.financial._constants import (
    FX_SENSITIVITY_HIGH,
    FX_SENSITIVITY_MODERATE,
    TREND_RSQUARED_HIGH,
    TREND_RSQUARED_MEDIUM,
)
from dartlab.analysis.financial._predictionSynthesis import (
    calcPredictionFlags,
    calcPredictionSynthesis,
)
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.core.utils.calc import safeDiv as _safe


def _getStockCode(company) -> str | None:
    """Company 객체에서 종목코드 추출."""
    return getattr(company, "stockCode", None)


def _getSectorKey(company) -> str | None:
    """업종 키 추출 (scenario.py와 동일 경로)."""
    try:
        from dartlab.analysis.financial.valuation import _IG_TO_SECTOR_KEY

        sectorInfo = company.sector
        if sectorInfo is not None:
            igName = sectorInfo.industryGroup.name
            return _IG_TO_SECTOR_KEY.get(igName)
    except (AttributeError, ValueError, ImportError):
        pass
    return None


# ══════════════════════════════════════
# calc 1: 이익 모멘텀/지속성
# ══════════════════════════════════════


@memoizedCalc
def calcEarningsMomentum(company, *, basePeriod: str | None = None) -> dict | None:
    """Sloan 분해 + DuPont 추세 → 이익 모멘텀 가속/감속 판정.

    Capabilities:
        Sloan (1996, AR) 의 현금 vs 발생액 분해와 DuPont 3 요소 (margin/
        turnover/leverage) 추세를 결합. 이익이 가속/감속/reversal 중 어느
        상태인지 + 현금 뒷받침 (OCF/NI) 강도를 함께 진단. predictionSignals
        의 5 신호 중 가장 핵심.

    Args:
        company: Company 객체. ``select("IS"|"CF"|"BS")`` 가능.
        basePeriod: 기준 기간. ``None`` 이면 최신.

    Returns:
        dict | None: 다음 키 (필수 데이터 누락 시 ``None``):
            - ``history`` (list[dict]): 연도별 Sloan 분해 (netIncome, ocf,
              accrual, sloanAccrualRatio, ocfToNi, margin, turnover, leverage)
            - ``momentum`` (str): ``"accelerating"``/``"decelerating"``/
              ``"reversing"``/``"stable"``
            - ``earningsDirection`` (str): ``"up"``/``"down"``/``"flat"``
            - ``persistenceScore`` (float): OCF/NI 평균 (점)
            - ``highAccrualWarning`` (bool): |accrual/자산| > 10% 경고
            - ``confidence`` (str): ``"high"``/``"medium"``/``"low"``

    Raises:
        없음.

    Example:
        >>> from dartlab import Company
        >>> r = calcEarningsMomentum(Company("005930"))
        >>> r["momentum"], r["highAccrualWarning"]
        ('accelerating', False)

    Guide:
        Sloan accrualRatio = (NI - OCF) / 평균자산. 양수 = 발생액 비중,
        음수 = 현금 우위. 10%+ 경고는 Sloan 의 earnings management 신호.
        DuPont 분해로 margin/turnover 중 어느 요인이 변화 주도하는지 표시.

    SeeAlso:
        - ``calcPredictionSynthesis``: 본 함수 결과 + 4 신호 앙상블
        - ``calcStructuralBreak``: 변동성 구조 변화 검증
        - Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals
          and Cash Flows?" The Accounting Review

    Requires:
        Company.select("IS", "당기순이익|매출액|영업이익") +
        Company.select("CF", "영업활동현금흐름") +
        Company.select("BS", "자산총계|자본총계").

    AIContext:
        ``highAccrualWarning=True`` 결과를 단독 인용해 "분식회계 의심" 으로
        결론 짓지 말 것 — Sloan 의 통계적 신호이지 의도 판정 아님.
        ``momentum`` 라벨과 함께 ``persistenceScore`` 도 노출.

    LLM Specifications:
        AntiPatterns:
            - 단년도 결과만으로 momentum 판정 — 최소 3 년 history 필요
              (confidence=low 결과는 호출자가 horizon 늘려 재호출).
            - 자본총계 < 0 (자본잠식) 회사 — DuPont leverage 비정상 (0 또는
              음수) → momentum 판정 신뢰도 낮음.
        OutputSchema:
            상기 6 키 dict.
        Prerequisites:
            IS/CF/BS 시계열 ≥ 3 년 + 자본총계 양수.
        Freshness:
            최신 보고기간 (분기). basePeriod 로 과거 시점 분석 가능.
        Dataflow:
            select(IS/CF/BS) → toDictBySnakeId → 연도별 NI/OCF/자산
            → Sloan accrual = NI - OCF → momentum 분류 → persistence.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    isResult = company.select("IS", ["당기순이익", "매출액", "영업이익"])
    cfResult = company.select("CF", ["영업활동현금흐름"])
    bsResult = company.select("BS", ["자산총계", "자본총계"])

    isParsed = toDictBySnakeId(isResult)
    cfParsed = toDictBySnakeId(cfResult)
    bsParsed = toDictBySnakeId(bsResult)
    if isParsed is None or cfParsed is None or bsParsed is None:
        return None

    isData, isPeriods = isParsed
    cfData, cfPeriods = cfParsed
    bsData, _ = bsParsed

    niRow = isData.get("당기순이익", {})
    revRow = isData.get("매출액", {})
    oiRow = isData.get("영업이익", {})
    ocfRow = cfData.get("영업활동현금흐름", {})
    taRow = bsData.get("자산총계", {})
    teRow = bsData.get("자본총계", {})

    yCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if len(yCols) < 3:
        return None

    # Phase 15 A1: Q4 함정 제거 — IS/CF flow 는 annualSumFlow (주석 실제 이행). BS 는 stock → 직접.
    from dartlab.core.utils.flow import annualSumFlow

    allIsPeriods = set(isPeriods)
    allCfPeriods = set(cfPeriods)

    history = []
    for col in yCols:
        ni = annualSumFlow(niRow, col, allIsPeriods, withFallback=True) or 0
        ocf = annualSumFlow(ocfRow, col, allCfPeriods, withFallback=True) or 0
        ta = _get(taRow, col)  # BS stock — Q4 가 연말잔액이라 그대로 OK
        rev = annualSumFlow(revRow, col, allIsPeriods, withFallback=True) or 0
        oi = annualSumFlow(oiRow, col, allIsPeriods, withFallback=True) or 0
        te = _get(teRow, col)  # BS stock
        accrual = ni - ocf

        margin = _safe(oi, rev) if rev != 0 else None
        turnover = _safe(rev, ta) if ta != 0 else None
        leverage = _safe(ta, te) if te != 0 else None

        history.append(
            {
                "period": col,
                "netIncome": ni,
                "ocf": ocf,
                "accrual": accrual,
                "sloanAccrualRatio": _safe(accrual, ta) if ta > 0 else None,
                "ocfToNi": _safe(ocf, ni) if ni != 0 else None,
                "margin": margin,
                "turnover": turnover,
                "leverage": leverage,
            }
        )

    if len(history) < 3:
        return None

    # 이익 방향성 판단 (최근 3년 추세)
    recentNi = [h["netIncome"] for h in history[:3]]
    niChanges = [recentNi[i] - recentNi[i + 1] for i in range(len(recentNi) - 1)]

    if all(d > 0 for d in niChanges):
        momentum = "accelerating"
        direction = "up"
    elif all(d < 0 for d in niChanges):
        momentum = "decelerating"
        direction = "down"
    elif len(niChanges) >= 2 and niChanges[0] > 0 and niChanges[1] < 0:
        momentum = "reversing"
        direction = "up"
    elif len(niChanges) >= 2 and niChanges[0] < 0 and niChanges[1] > 0:
        momentum = "reversing"
        direction = "down"
    else:
        momentum = "stable"
        direction = "flat"

    # 현금 지속성 점수 (OCF/NI 비율 기반)
    ocfToNiVals = [h["ocfToNi"] for h in history[:5] if h["ocfToNi"] is not None]
    if ocfToNiVals:
        avgOcfToNi = sum(ocfToNiVals) / len(ocfToNiVals)
        if avgOcfToNi >= 1.0:
            persistenceScore = min(90, 50 + avgOcfToNi * 20)
        elif avgOcfToNi >= 0.5:
            persistenceScore = 30 + avgOcfToNi * 40
        else:
            persistenceScore = max(10, avgOcfToNi * 60)
    else:
        persistenceScore = 50

    # 발생액 비율 기반 경고
    recentAccrual = [h["sloanAccrualRatio"] for h in history[:3] if h["sloanAccrualRatio"] is not None]
    highAccrual = any(abs(a) > 0.10 for a in recentAccrual) if recentAccrual else False

    # 신뢰도
    nYears = len(history)
    if nYears >= 5 and not highAccrual:
        confidence = "high"
    elif nYears >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "history": history,
        "momentum": momentum,
        "earningsDirection": direction,
        "persistenceScore": round(persistenceScore, 1),
        "highAccrualWarning": highAccrual,
        "confidence": confidence,
    }


# ══════════════════════════════════════


# 분리된 신호 (BC re-export)
from dartlab.analysis.financial._signalsCorporate import (  # noqa: E402, F401
    calcAnnouncementTiming,
    calcDisclosureDelta,
    calcInventoryDivergence,
    calcSupplyChainSignal,
)
from dartlab.analysis.financial._signalsDirection import (  # noqa: E402, F401
    calcConsensusDirection,
    calcFlowDirection,
    calcRevenueDirection,
)
from dartlab.analysis.financial._signalsEvent import calcEventImpact  # noqa: E402, F401
from dartlab.analysis.financial._signalsMacro import (  # noqa: E402, F401
    calcMacroRegression,
    calcMacroSensitivity,
    calcStructuralBreak,
)
from dartlab.analysis.financial._signalsPeer import calcPeerPrediction  # noqa: E402, F401
