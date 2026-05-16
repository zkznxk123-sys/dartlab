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
# calc 2: 횡단면 피어 예측
# ══════════════════════════════════════


@memoizedCalc
def calcPeerPrediction(company, *, basePeriod: str | None = None) -> dict | None:
    """Cross-section + panel 회귀 → peer 기반 매출 성장률 예측 + 괴리.

    Capabilities:
        scan 의 사전 적합된 횡단면/패널 OLS 모델 (loadModel/loadPanelModel)
        로 이 회사의 향후 매출 성장률 (%) 을 예측. 실제 historical 성장률과
        의 괴리 (divergence) 를 측정해 outlier 시그널 산출. 5 신호 중 cross-
        section 기반 신호.

    Args:
        company: Company 객체. stockCode + 재무 시계열 필요.
        basePeriod: 기준 기간. None 이면 최신.

    Returns:
        dict | None: 다음 키 (모델/데이터 부족 시 ``None``):
            - ``crossSectionPredicted`` (float|None): 횡단면 OLS 예측 (%)
            - ``panelPredicted`` (float|None): 패널 모델 예측 (%)
            - ``ensemblePredicted`` (float): 두 모델 평균 (없으면 단일)
            - ``companyHistoricalGrowth`` (float|None): 실제 매출 성장률 (%)
            - ``divergence`` (float|None): 예측 - 실제 (%p)
            - ``modelR2`` (float|None): 횡단면 모델 R²

    Raises:
        없음.

    Example:
        >>> r = calcPeerPrediction(Company("005930"))
        >>> r["ensemblePredicted"], r["divergence"]
        (8.5, -2.3)  # 모델은 8.5% 예측, 실제는 10.8% (peer 대비 outperform)

    Guide:
        divergence > 0 → 모델보다 실제가 낮음 (peer 평균 하회). divergence
        < 0 → outperform. |divergence| > 5%p 면 outlier (peer 대비 크게
        다른 트랙). 모델 R² < 0.3 이면 예측 신뢰도 낮음.

    SeeAlso:
        - ``loadModel``/``loadPanelModel``: 횡단면/패널 모델 로드
        - ``calcPredictionSynthesis``: 본 함수 + 4 신호 앙상블

    Requires:
        scan 사전 적합 모델 (year-1 ~ year-3 탐색) + Company 재무 시계열.

    AIContext:
        ensemblePredicted 단독 인용 금지 — modelR2 와 divergence 함께. R²
        낮은 (<0.3) 모델 예측은 informative 가 아니라 noise 신호.

    LLM Specifications:
        AntiPatterns:
            - 모델이 없는 신규 산업/IPO 종목 — None 반환, 호출자 fallback
              로직 필요.
            - divergence 부호 해석 오류 — divergence>0 = 실제가 낮음 (peer
              하회), <0 = outperform.
        OutputSchema:
            상기 6 키 dict.
        Prerequisites:
            scan/loadModel(year) 결과 존재 + Company 재무 ≥ 3 년.
        Freshness:
            모델 = 연 1 회 적합 (loadModel year 인자).
        Dataflow:
            stockCode → loadModel/loadPanelModel → company features →
            예측 → ensemble → historical 비교 → divergence.
        TargetMarkets: KR (scan SSOT). US 미적용 (모델 부재).
    """
    stockCode = _getStockCode(company)
    if stockCode is None:
        return None

    # 횡단면 모델 로드 시도 (최신 연도부터 탐색)
    from datetime import datetime

    try:
        from dartlab.analysis.valuation.crossRegression import loadModel, loadPanelModel

        csModel = None
        for tryYear in range(datetime.now().year - 1, datetime.now().year - 4, -1):
            csModel = loadModel(tryYear)
            if csModel is not None:
                break
        panelModel = loadPanelModel()
    except (ImportError, FileNotFoundError, OSError, TypeError):
        csModel = None
        panelModel = None

    if csModel is None and panelModel is None:
        return None

    # 이 회사 피처 추출 (scan ratio에서)
    features = _extractPeerFeatures(company)
    if features is None:
        return None

    sectorKey = _getSectorKey(company) or ""

    # 횡단면 예측
    csPredicted = None
    csR2 = None
    if csModel is not None:
        csPredicted = csModel.predict(features, sectorKey)
        csR2 = csModel.rSquared

    # 패널 예측
    panelPredicted = None
    if panelModel is not None:
        panelPredicted = panelModel.predict(stockCode, features)

    # 앙상블 (단순 평균 — 학술적 최적)
    preds = [p for p in [csPredicted, panelPredicted] if p is not None]
    if not preds:
        return None

    ensemblePredicted = sum(preds) / len(preds)

    # 실제 매출 성장률
    historicalGrowth = _getHistoricalRevenueGrowth(company, basePeriod=basePeriod)

    divergence = None
    if historicalGrowth is not None:
        divergence = ensemblePredicted - historicalGrowth

    return {
        "crossSectionPredicted": round(csPredicted, 2) if csPredicted is not None else None,
        "panelPredicted": round(panelPredicted, 2) if panelPredicted is not None else None,
        "ensemblePredicted": round(ensemblePredicted, 2),
        "companyHistoricalGrowth": round(historicalGrowth, 2) if historicalGrowth is not None else None,
        "divergence": round(divergence, 2) if divergence is not None else None,
        "modelR2": round(csR2, 3) if csR2 is not None else None,
    }


def _extractPeerFeatures(company) -> dict[str, float] | None:
    """company에서 횡단면 회귀 피처를 추출."""
    features: dict[str, float] = {}

    try:
        ratios = company._getRatiosInternal()
        if ratios is None:
            return None

        per = getattr(ratios, "per", None)
        pbr = getattr(ratios, "pbr", None)
        opMargin = getattr(ratios, "operatingMargin", None)
        debtRatio = getattr(ratios, "debtRatio", None)

        if per is not None:
            features["per"] = per
        if pbr is not None:
            features["pbr"] = pbr
        if opMargin is not None:
            features["operatingMargin"] = opMargin
        if debtRatio is not None:
            features["debtRatio"] = debtRatio

        # lnMarketCap
        profile = getattr(company, "profile", None)
        if profile:
            mc = getattr(profile, "marketCap", None)
            if mc and mc > 0:
                features["lnMarketCap"] = math.log(mc)

        # capexRatio, foreignHoldingRatio, revenueGrowthLag — 없으면 기본값
        features.setdefault("capexRatio", 0.0)
        features.setdefault("foreignHoldingRatio", 0.0)
        features.setdefault("revenueGrowthLag", 0.0)

    except (AttributeError, TypeError, ValueError):
        return None

    # 최소 4개 피처 있어야 유의미
    if len(features) < 4:
        return None

    return features


def _getHistoricalRevenueGrowth(company, *, basePeriod: str | None = None) -> float | None:
    """최근 매출 성장률 (%) 계산."""
    isResult = company.select("IS", ["매출액"])
    parsed = toDictBySnakeId(isResult)
    if parsed is None:
        return None
    data, periods = parsed
    revRow = data.get("매출액", {})
    yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=3)
    if len(yCols) < 2:
        return None
    cur = _get(revRow, yCols[0])
    prev = _get(revRow, yCols[1])
    if prev == 0:
        return None
    return ((cur - prev) / abs(prev)) * 100


# ══════════════════════════════════════
# calc 3: 구조변화 감지
# ══════════════════════════════════════


@memoizedCalc
def calcStructuralBreak(company, *, basePeriod: str | None = None) -> dict | None:
    """Chow Test → 매출/영업이익/마진/ROE 구조변화점 감지 + 추세 신뢰도.

    Capabilities:
        Chow Test (1960) 의 dummy variable F-test 로 4 대 지표의 break year
        를 탐색. break 전후 평균 성장률 비교로 트렌드 안정성 판정. predicition
        모델의 horizon 결정 시 신뢰도 입력 (break 이후 데이터만 사용 권장).

    Args:
        company: Company 객체. IS 시계열 ≥ 6 년 필요.
        basePeriod: 기준 기간. None 이면 최신.

    Returns:
        dict | None: 다음 키 (6 년 미만 시 ``None``):
            - ``metrics`` (list[dict]): 4 지표별:
                * ``name`` (str): revenue/operatingIncome/operatingMargin/roe
                * ``hasBreak`` (bool): break 존재 여부 (Chow F > 임계)
                * ``breakYear`` (str|None): break 시점
                * ``preBreakGrowth``/``postBreakGrowth`` (float|None): 평균 성장률
                * ``trendReliability`` (str): high/medium/low
                * ``nObservations`` (int)
            - ``overallStability`` (str): ``"stable"``/``"transitioning"``/
              ``"volatile"`` (4 지표 합산)

    Raises:
        없음.

    Example:
        >>> r = calcStructuralBreak(Company("005930"))
        >>> r["overallStability"]
        'stable'
        >>> [m["name"] for m in r["metrics"] if m["hasBreak"]]
        ['operatingMargin']  # 마진만 구조변화

    Guide:
        Chow Test 임계: F > 5 = high break. preBreakGrowth vs postBreakGrowth
        부호 반전 시 reversing trend — DCF/forecastRevenue 의 horizon 단축
        권장 (break 이후 데이터만 사용). 6 년 미만 회사는 break 탐지 불가.

    SeeAlso:
        - ``dartlab.core.utils.ols.detectStructuralBreak``: Chow Test 본체
        - ``calcMacroRegression``: 매크로 회귀에서 break 인지 분기

    Requires:
        IS 시계열 ≥ 6 년 + 매출액/영업이익 데이터.

    AIContext:
        ``overallStability="volatile"`` 회사는 모든 forecast 결과 신뢰도
        하향. break year 가 외부 충격 (코로나/금융위기) 과 일치하면
        natural break — 회사 fundamentals 변화로 해석 금지.

    LLM Specifications:
        AntiPatterns:
            - hasBreak=True 만 보고 즉시 "트렌드 깨짐" 단정 금지 — preBreak
              vs postBreak 평균 비교 후 가속/감속/reversal 분류.
            - 6 년 미만 회사에 본 함수 호출 → None — 호출자 분기 필요.
        OutputSchema:
            ``{metrics: list[dict 7키], overallStability: str}``.
        Prerequisites:
            IS 시계열 ≥ 6 년 + ``ols.detectStructuralBreak`` 로드 가능.
        Freshness:
            IS 의 freshness (최신 분기).
        Dataflow:
            IS 시계열 → 4 지표 추출 → Chow Test (각 year split) → F-stat
            max → break year → pre/post 평균 → overall 합산.
        TargetMarkets: KR (DART), US (EDGAR).
    """
    from dartlab.core.utils.ols import detectStructuralBreak, ols

    isResult = company.select("IS", ["매출액", "영업이익"])
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None
    isData, isPeriods = isParsed

    revRow = isData.get("매출액", {})
    oiRow = isData.get("영업이익", {})
    yCols = annualColsFromPeriods(isPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if len(yCols) < 6:
        return None

    # ROE 시계열 (ratioSeries에서)
    roeVals = _getRatioValues(company, "roe", len(yCols))

    # 4대 지표 시계열 (오래된 → 최신 순서로 뒤집기)
    metrics = []

    revVals = [_get(revRow, c) for c in reversed(yCols)]
    oiVals = [_get(oiRow, c) for c in reversed(yCols)]
    marginVals = [
        _safe(oi, rev) * 100 if rev != 0 and _safe(oi, rev) is not None else None for rev, oi in zip(revVals, oiVals)
    ]

    for name, vals in [
        ("revenue", revVals),
        ("operatingIncome", oiVals),
        ("operatingMargin", marginVals),
        ("roe", roeVals),
    ]:
        clean = [v for v in vals if v is not None]
        if len(clean) < 6:
            metrics.append(
                {
                    "name": name,
                    "hasBreak": False,
                    "breakYear": None,
                    "preBreakGrowth": None,
                    "postBreakGrowth": None,
                    "trendReliability": "low",
                    "nObservations": len(clean),
                }
            )
            continue

        breakIdx = detectStructuralBreak(clean)

        if breakIdx is not None:
            # 변화점 기준 전/후 성장률
            pre = clean[:breakIdx]
            post = clean[breakIdx:]
            preGrowth = _avgGrowth(pre)
            postGrowth = _avgGrowth(post)

            # 연도 매핑 (reversed yCols 기준)
            reversedCols = list(reversed(yCols))
            breakYear = reversedCols[breakIdx] if breakIdx < len(reversedCols) else None

            metrics.append(
                {
                    "name": name,
                    "hasBreak": True,
                    "breakYear": breakYear,
                    "preBreakGrowth": round(preGrowth, 2) if preGrowth is not None else None,
                    "postBreakGrowth": round(postGrowth, 2) if postGrowth is not None else None,
                    "trendReliability": "low",
                    "nObservations": len(clean),
                }
            )
        else:
            # 변화점 없음 — 추세 일관
            _, _, r2 = ols(list(range(len(clean))), clean)
            reliability = "high" if r2 > TREND_RSQUARED_HIGH else ("medium" if r2 > TREND_RSQUARED_MEDIUM else "low")
            metrics.append(
                {
                    "name": name,
                    "hasBreak": False,
                    "breakYear": None,
                    "preBreakGrowth": None,
                    "postBreakGrowth": None,
                    "trendReliability": reliability,
                    "nObservations": len(clean),
                }
            )

    # 전체 안정성 판단
    nBreaks = sum(1 for m in metrics if m["hasBreak"])
    if nBreaks == 0:
        overallStability = "stable"
    elif nBreaks <= 1:
        overallStability = "transitioning"
    else:
        overallStability = "volatile"

    return {
        "metrics": metrics,
        "overallStability": overallStability,
    }


def _getRatioValues(company, ratioName: str, maxYears: int) -> list[float | None]:
    """ratioSeries에서 특정 비율의 시계열을 추출."""
    try:
        from dartlab.analysis.financial.companyContext import getRatioSeries

        result = getRatioSeries(company)
        if result is None:
            return []
        data, years = result
        vals = data.get("RATIO", {}).get(ratioName, [])
        # 최신 maxYears개, 오래된→최신 순서로
        if len(vals) > maxYears:
            vals = vals[-maxYears:]
        return vals
    except (AttributeError, TypeError, ValueError):
        return []


def _avgGrowth(vals: list[float]) -> float | None:
    """값 목록의 평균 성장률 (%)."""
    if len(vals) < 2:
        return None
    growths = []
    for i in range(1, len(vals)):
        if vals[i - 1] != 0:
            growths.append(((vals[i] - vals[i - 1]) / abs(vals[i - 1])) * 100)
    return sum(growths) / len(growths) if growths else None


# ══════════════════════════════════════
# calc 4: 거시경제 민감도
# ══════════════════════════════════════


@memoizedCalc
def calcMacroSensitivity(company, *, basePeriod: str | None = None) -> dict | None:
    """거시경제 민감도 — 섹터별 탄성치 + 관련 지표 매핑.

    라이브 매크로 데이터를 fetch하지 않는다.
    관련 지표명을 반환하여 AI가 gather.macro()로 조회할 수 있게 한다.

    Returns
    -------
    dict
        sectorKey : str | None — 업종 키
        sectorCyclicality : str — 경기순환 민감도 ("high" | "moderate" | "low")
        revenueToGdp : float — 매출-GDP 탄성치 (배수)
        revenueToFx : float — 매출-환율 탄성치 (배수)
        marginToGdp : float — 마진-GDP 탄성치 (배수)
        fxExposure : str — 환율 노출 ("high" | "moderate" | "low")
        commodityExposure : str — 원자재 노출 ("high" | "low")
        rateSensitivity : str — 금리 민감도 ("high" | "low")
        primaryDrivers : list[dict] — 1차 거시 동인 (indicator, source, direction, description)
        secondaryDrivers : list[dict] — 2차 거시 동인
        relevantIndicators : list[str] — 관련 지표 ID 목록
        predictionAxes : dict | None — 라이브 축 상태 (PredictionSpace 캐시 있을 때)
        axisImpact : dict | None — 업종별 축 영향도
        netMacroEffect : float | None — 순 매크로 효과 합산
    """
    from dartlab.synth.scenario import getElasticity

    sectorKey = _getSectorKey(company)
    elasticity = getElasticity(sectorKey)

    # 민감도 분류
    fxExposure = (
        "high"
        if abs(elasticity.revenueToFx) >= FX_SENSITIVITY_HIGH
        else ("moderate" if abs(elasticity.revenueToFx) >= FX_SENSITIVITY_MODERATE else "low")
    )
    commodityExposure = "high" if sectorKey in _COMMODITY_SECTORS else "low"
    rateSensitivity = "high" if (sectorKey in _RATE_SENSITIVE_SECTORS or elasticity.nimToRate > 0) else "low"

    # 관련 지표 매핑
    drivers = _SECTOR_MACRO_MAP.get(elasticity.cyclicality, _SECTOR_MACRO_MAP["moderate"])
    primaryDrivers = drivers[:2] if len(drivers) >= 2 else drivers
    secondaryDrivers = drivers[2:] if len(drivers) > 2 else []

    # 금리 민감 섹터 추가 지표
    if rateSensitivity == "high":
        primaryDrivers = [
            {
                "indicator": "BASE_RATE",
                "source": "ECOS",
                "direction": "direct",
                "description": "기준금리 → NIM 직접 영향",
            },
        ] + primaryDrivers

    # FX 민감 섹터 추가 지표
    if fxExposure == "high":
        secondaryDrivers.append(
            {
                "indicator": "KRW_USD",
                "source": "ECOS",
                "direction": "positive_for_export",
                "description": "원화 약세 → 수출 유리",
            }
        )

    # 관련 지표명 목록 (AI가 gather.macro()로 조회할 때 사용)
    allIndicators = list({d["indicator"] for d in primaryDrivers + secondaryDrivers})

    result = {
        "sectorKey": sectorKey,
        "sectorCyclicality": elasticity.cyclicality,
        "revenueToGdp": elasticity.revenueToGdp,
        "revenueToFx": elasticity.revenueToFx,
        "marginToGdp": elasticity.marginToGdp,
        "fxExposure": fxExposure,
        "commodityExposure": commodityExposure,
        "rateSensitivity": rateSensitivity,
        "primaryDrivers": primaryDrivers,
        "secondaryDrivers": secondaryDrivers,
        "relevantIndicators": allIndicators,
    }

    # Prediction Space enrichment (라이브 축 상태, 캐시 있을 때만)
    try:
        from dartlab.analysis.forecast.predictionSpace import getPredictionSpace

        space = getPredictionSpace()
        if space is not None:
            result["predictionAxes"] = {
                name: {
                    "label": ax.label,
                    "level": ax.level,
                    "direction": ax.direction,
                    "momentum": ax.momentum,
                }
                for name, ax in space.axes.items()
            }
            result["axisImpact"] = space.impactOn(sectorKey)
            result["netMacroEffect"] = round(sum(space.impactOn(sectorKey).values()), 2)
    except (ImportError, TypeError):
        pass

    return result


# ══════════════════════════════════════
# calc 4b: 거시-재무 동적 회귀
# ══════════════════════════════════════


@memoizedCalc
def calcMacroRegression(company, *, basePeriod: str | None = None) -> dict | None:
    """거시-재무 동적 회귀 — 기업별 거시 베타를 과거 데이터에서 학습.

    정적 상수(scenario.py의 revenueToGdp=1.8 등) 대신,
    실제 과거 매출/마진 성장률과 거시지표 변화율 간 OLS 회귀로
    기업 고유의 동적 베타를 추정한다.

    학술 근거:
    - Fama-MacBeth 1973: 횡단면 회귀로 팩터 프리미엄 추정
    - 시간차(lag) 효과: GDP t → 매출 t+1 (경기 전달 메커니즘)

    Returns
    -------
    dict
        betas : dict[str, float] — OLS 기울기 (기업 고유 동적 베타, 변수별)
        staticBetas : dict[str, float] — 정적 탄성치 (gdp, rate, fx) (배수)
        usedIndicators : dict[str, str] — 사용된 지표 매핑 (v0→seriesId)
        marginBetas : dict[str, float] | None — 마진 회귀 OLS 기울기
        lagEffects : dict[str, dict] — 시간차별 상관도 (lag0, lag1, lag2)
        rSquared : float — 매출 회귀 R-squared
        marginR2 : float | None — 마진 회귀 R-squared
        nObs : int — 관측치 수
        nVars : int — 변수 수
        degreesOfFreedom : int — 자유도
        confidence : str — 신뢰도 ("high" | "medium" | "low")
        sectorKey : str | None — 업종 키
        table : list[dict] — 기간별 매출 성장률 vs 거시 변화율 시계열
    """
    isResult = company.select("IS", ["매출액", "영업이익"])
    isParsed = toDictBySnakeId(isResult)
    if isParsed is None:
        return None
    isData, isPeriods = isParsed
    revRow = isData.get("매출액", {})
    oiRow = isData.get("영업이익", {})

    # 분기 YoY 기반: 동일 분기 대비 성장률 (관측치 ~36개)
    qCols = sorted([p for p in isPeriods if "Q" in p], reverse=True)
    yoyCols: list[str] = []
    revGrowth: list[float | None] = []
    marginChange: list[float | None] = []

    for col in qCols:
        prevCol = f"{int(col[:4]) - 1}{col[-2:]}"
        if prevCol not in isPeriods:
            continue
        cur = _get(revRow, col) or None
        prev = _get(revRow, prevCol) or None
        if cur is not None and prev is not None and prev != 0:
            revGrowth.append((cur - prev) / abs(prev) * 100)
        else:
            revGrowth.append(None)

        curOi = _get(oiRow, col) or None
        prevOi = _get(oiRow, prevCol) or None
        curMargin = curOi / cur * 100 if cur and curOi and cur != 0 else None
        prevMargin = prevOi / prev * 100 if prev and prevOi and prev != 0 else None
        if curMargin is not None and prevMargin is not None:
            marginChange.append(curMargin - prevMargin)
        else:
            marginChange.append(None)

        yoyCols.append(col)

    cols = yoyCols
    if len(cols) < 6:
        return None

    # 적응형 변수 선택: 매핑 후보 + 범용 후보에서 상관도 기반 최적 3개
    stockCode = _getStockCode(company)
    macroData = _loadAdaptive(revGrowth, cols, stockCode=stockCode)
    if macroData is None:
        return None

    # OLS 회귀
    betas, rSquared, nObs = _fitOLS(revGrowth, macroData, cols)
    if betas is None:
        return None

    # 시간차(lag) 상관도 계산
    lagEffects = _calcLagCorrelation(revGrowth, macroData, cols)

    # 마진 회귀 (금리 → 마진 변화)
    marginBetas, marginR2, _ = _fitOLS(marginChange, macroData, cols)

    # 정적 탄성치 비교
    from dartlab.synth.scenario import getElasticity

    sectorKey = _getSectorKey(company)
    staticEl = getElasticity(sectorKey)

    confidence = "high" if nObs >= 8 and rSquared > 0.3 else ("medium" if nObs >= 5 else "low")

    # 테이블 (연도별 시계열)
    table = _buildMacroTable(cols, revGrowth, marginChange, macroData)

    # 사용된 지표 정보
    usedIndicators = macroData.get("_usedIndicators", {}) if isinstance(macroData.get("_usedIndicators"), dict) else {}

    return {
        "betas": betas,
        "staticBetas": {
            "gdp": staticEl.revenueToGdp,
            "rate": staticEl.marginToGdp,
            "fx": staticEl.revenueToFx,
        },
        "usedIndicators": usedIndicators,
        "marginBetas": marginBetas,
        "lagEffects": lagEffects,
        "rSquared": round(rSquared, 4),
        "marginR2": round(marginR2, 4) if marginR2 is not None else None,
        "nObs": nObs,
        "nVars": len(betas) if betas else 0,
        "degreesOfFreedom": nObs - len(betas) - 1 if betas else 0,
        "confidence": confidence,
        "sectorKey": sectorKey,
        "table": table,
        "_predictedDirection": _predictDirection(betas, macroData),
    }


def _predictDirection(betas: dict | None, macroData: dict) -> str | None:
    """OLS 베타 × 최신 외생변수 변화율 → 예측 방향."""
    if not betas:
        return None
    # macroData의 첫 번째 값(최신)을 사용
    predicted = 0.0
    for key, beta in betas.items():
        vals = macroData.get(key)
        if isinstance(vals, list) and vals and vals[0] is not None:
            predicted += beta * vals[0]
    return "up" if predicted > 0 else "down"


def _getFinanceSeries(company):
    """Company 에서 finance series-tuple 추출 (private internal)."""
    try:
        result = company._buildFinanceSeries(freq="Q")
        return result[0] if result else None
    except (AttributeError, TypeError):
        return None


def _loadAdaptive(
    revGrowth: list[float | None], periodCols: list[str], stockCode: str | None = None
) -> dict[str, list[float | None]] | None:
    """적응형 변수 선택 — 매핑 후보 + 범용 후보에서 상관도 기반 최적 3개.

    1. exogenousAxes 매핑 3개 + 범용 후보 5개 = 총 8개 로드
    2. 각 변수와 revGrowth의 상관도 계산
    3. 상관도 상위 3개 선택
    """
    from dartlab.gather.transforms.macro import alignToFinancialPeriods, loadMacroParquet

    # 매핑 후보
    try:
        from dartlab.gather.mapping.exogenousAxes import getExogenousSeriesIds

        mapped = getExogenousSeriesIds(stockCode=stockCode)
    except (ImportError, KeyError):
        mapped = [("IPI", "ecos"), ("BASE_RATE", "ecos"), ("USDKRW", "ecos")]

    # 범용 후보 (전 시장에서 빈출 + 한국 PPI)
    universal = [
        ("PPI_MFG", "ecos"),  # 한국 공산품PPI — 가장 직접적 범용
        ("PCUOMFGOMFG", "fred"),  # 미국 제조업PPI
        ("EXPORT", "ecos"),  # 한국 수출
        ("PCOPPUSDM", "fred"),  # 구리 (글로벌 수요)
        ("INDPRO", "fred"),  # 미국 산업생산
        ("TCU", "fred"),  # 설비가동률
        ("DGORDER", "fred"),  # 내구재 주문
    ]

    # 중복 제거하며 합치기
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []
    for sid, src in mapped + universal:
        if sid not in seen:
            seen.add(sid)
            candidates.append((sid, src))

    # 전년동기 기간 생성
    prevCols = [f"{int(c[:4]) - 1}{c[4:]}" for c in periodCols]
    isRateVar = {"BASE_RATE", "BAMLH0A0HYM2", "CORP_BOND_3Y"}

    # 모든 후보 로드 + YoY 계산 + 상관도
    candidateData: list[tuple[str, str, list[float | None], float]] = []

    for sid, source in candidates:
        df = loadMacroParquet(sid, source=source)
        if isEmptyDf(df):
            continue
        curVals = alignToFinancialPeriods(df, periodCols).get_column("value").to_list()
        prevVals = alignToFinancialPeriods(df, prevCols).get_column("value").to_list()

        changes: list[float | None] = []
        for cur, prev in zip(curVals, prevVals):
            if cur is not None and prev is not None and prev != 0:
                changes.append(cur - prev if sid in isRateVar else (cur - prev) / abs(prev) * 100)
            else:
                changes.append(None)

        # 상관도 계산
        corr = _quickCorr(revGrowth, changes)
        candidateData.append((sid, source, changes, abs(corr) if corr is not None else 0))

    if not candidateData:
        return None

    # 상관도 상위 3개 선택
    candidateData.sort(key=lambda x: x[3], reverse=True)
    selected = candidateData[:3]

    result: dict[str, list[float | None]] = {}
    usedIndicators: dict[str, str] = {}

    for i, (sid, source, changes, corr) in enumerate(selected):
        key = f"v{i}"
        result[key] = changes
        usedIndicators[key] = sid

    result["_usedIndicators"] = usedIndicators  # type: ignore[assignment]
    return result


def _loadMacroAligned(periodCols: list[str], stockCode: str | None = None) -> dict[str, list[float | None]] | None:
    """Parquet 캐시에서 거시 지표를 로드 → YoY 변화율을 직접 계산.

    periodCols가 분기("2024Q3" 등)이면 전년동기 대비 YoY,
    연간이면 전년 대비 변화율.

    Returns:
        {"v0": [yoy_change, ...], "v1": [...], "_usedIndicators": {...}}
        또는 None (데이터 없음).
    """
    from dartlab.gather.transforms.macro import alignToFinancialPeriods, loadMacroParquet

    try:
        from dartlab.gather.mapping.exogenousAxes import getExogenousSeriesIds

        seriesPairs = getExogenousSeriesIds(stockCode=stockCode)
    except (ImportError, KeyError):
        seriesPairs = [("IPI", "ecos"), ("BASE_RATE", "ecos"), ("USDKRW", "ecos")]

    # 전년동기 기간 생성
    prevCols = [f"{int(c[:4]) - 1}{c[4:]}" for c in periodCols]

    result: dict[str, list[float | None]] = {}
    usedIndicators: dict[str, str] = {}
    isRateVar = {"BASE_RATE", "BAMLH0A0HYM2", "CORP_BOND_3Y"}

    for i, (seriesId, source) in enumerate(seriesPairs[:3]):
        key = f"v{i}"
        df = loadMacroParquet(seriesId, source=source)
        if df is not None and not df.is_empty():
            curVals = alignToFinancialPeriods(df, periodCols).get_column("value").to_list()
            prevVals = alignToFinancialPeriods(df, prevCols).get_column("value").to_list()

            # YoY 변화율 계산
            changes: list[float | None] = []
            for cur, prev in zip(curVals, prevVals):
                if cur is not None and prev is not None and prev != 0:
                    if seriesId in isRateVar:
                        changes.append(cur - prev)  # 금리: 절대 변화 (pp)
                    else:
                        changes.append((cur - prev) / abs(prev) * 100)  # %
                else:
                    changes.append(None)
            result[key] = changes
            usedIndicators[key] = seriesId
        else:
            result[key] = [None] * len(periodCols)
            usedIndicators[key] = seriesId

    result["_usedIndicators"] = usedIndicators  # type: ignore[assignment]

    hasData = any(
        any(v is not None for v in vals)
        for k, vals in result.items()
        if k != "_usedIndicators" and isinstance(vals, list)
    )
    return result if hasData else None


def _buildMacroTable(
    cols: list[str],
    revGrowth: list[float | None],
    marginChange: list[float | None],
    macroData: dict[str, list[float | None]],
) -> list[dict]:
    """연도별 매출 성장률 vs 거시 변화율 시계열 테이블."""
    table = []
    n = min(len(revGrowth), len(cols) - 1)

    for i in range(n):
        row: dict = {
            "period": cols[i],
            "revGrowthPct": round(revGrowth[i], 2) if revGrowth[i] is not None else None,
            "marginChangeBps": round(marginChange[i], 1)
            if i < len(marginChange) and marginChange[i] is not None
            else None,
        }
        for key, vals in macroData.items():
            if key == "_usedIndicators" or not isinstance(vals, list):
                continue
            row[f"{key}Value"] = round(vals[i], 2) if i < len(vals) and vals[i] is not None else None
        table.append(row)

    return table


# ══════════════════════════════════════
# calc 5: 공시 변화 신호
# ══════════════════════════════════════


@memoizedCalc
def calcDisclosureDelta(company, *, basePeriod: str | None = None) -> dict | None:
    """공시 변화 신호 — diff 결과를 예측 신호로 변환.

    공시 텍스트 변화량을 방향성 신호로 해석한다.
    FinBERT 등 톤 분석은 미적용 — 변화 크기만 사용.

    Returns
    -------
    dict
        overallChangeRate : float — 전체 공시 변화율 (%)
        riskChangeRate : float — 리스크 관련 토픽 변화율 (%)
        businessChangeRate : float — 사업 관련 토픽 변화율 (%)
        revenueRelatedChange : float — 매출 관련 토픽 변화율 (%)
        signalDirection : str — 방향성 ("positive" | "negative" | "neutral")
        signalStrength : str — 신호 강도 ("strong" | "moderate" | "weak")
        topChangedTopics : list[dict] — 변화율 상위 5개 토픽 (topic, changeRate)
    """
    try:
        diffResult = company._docs.diff()
    except (AttributeError, TypeError):
        return None

    if diffResult is None:
        return None

    overallChangeRate = getattr(diffResult, "changeRate", None) or 0.0

    # 토픽별 변화율 추출
    riskChangeRate = 0.0
    businessChangeRate = 0.0
    revenueChangeRate = 0.0
    topChangedTopics = []

    riskTopics = {"riskFactors", "riskDerivative", "contingentLiabilities"}
    businessTopics = {"businessOverview", "businessContent"}
    revenueTopics = {"revenue", "salesSegment", "productionStatus"}

    topicChanges = getattr(diffResult, "topicChanges", None) or []
    for tc in topicChanges:
        topic = getattr(tc, "topic", "")
        changeRate = getattr(tc, "changeRate", 0) or 0

        if topic in riskTopics:
            riskChangeRate = max(riskChangeRate, changeRate)
        elif topic in businessTopics:
            businessChangeRate = max(businessChangeRate, changeRate)
        elif topic in revenueTopics:
            revenueChangeRate = max(revenueChangeRate, changeRate)

        if changeRate > 20:
            topChangedTopics.append({"topic": topic, "changeRate": round(changeRate, 1)})

    # 방향성 신호 판단
    if riskChangeRate > 60:
        signalDirection = "negative"
        signalStrength = "strong"
    elif riskChangeRate > 30:
        signalDirection = "negative"
        signalStrength = "moderate"
    elif overallChangeRate < 10:
        signalDirection = "neutral"
        signalStrength = "weak"
    elif businessChangeRate > 40 and riskChangeRate < 20:
        signalDirection = "positive"
        signalStrength = "moderate"
    else:
        signalDirection = "neutral"
        signalStrength = "weak"

    # 변화 큰 토픽 정렬
    topChangedTopics.sort(key=lambda x: x["changeRate"], reverse=True)

    return {
        "overallChangeRate": round(overallChangeRate, 1),
        "riskChangeRate": round(riskChangeRate, 1),
        "businessChangeRate": round(businessChangeRate, 1),
        "revenueRelatedChange": round(revenueChangeRate, 1),
        "signalDirection": signalDirection,
        "signalStrength": signalStrength,
        "topChangedTopics": topChangedTopics[:5],
    }


# ══════════════════════════════════════
# calc 8: 재고/매출채권 괴리 신호
# ══════════════════════════════════════


@memoizedCalc
def calcInventoryDivergence(company, *, basePeriod: str | None = None) -> dict | None:
    """재고/매출채권 괴리 — 수요 둔화 선행 지표.

    재고 증가율 > 매출 증가율 = 수요 둔화 (NYU Stern).
    매출채권 증가율 > 매출 증가율 = 회수 악화.
    NOA 급증 = 이익 조작 가능성 (Oler 2024).

    Returns
    -------
    dict
        history : list[dict] — 연도별 시계열 (inventory, receivables, revenue, inventoryGrowth(%), revenueGrowth(%), divergence(%p), arDivergence(%p), dso(일), dio(일), noa(원))
        inventorySignal : str — 재고 신호 ("building" | "liquidating" | "stable")
        receivableSignal : str — 매출채권 신호 ("deteriorating" | "improving" | "stable")
        noaGrowth : float | None — NOA 성장률 (%)
        riskScore : int — 리스크 점수 (점, 0-100)
    """
    bsResult = company.select(
        "BS", ["재고자산", "매출채권및기타채권", "매출채권", "매입채무및기타채무", "매입채무", "자산총계"]
    )
    isResult = company.select("IS", ["매출액", "매출원가"])

    bsParsed = toDictBySnakeId(bsResult)
    isParsed = toDictBySnakeId(isResult)
    if bsParsed is None or isParsed is None:
        return None

    bsData, bsPeriods = bsParsed
    isData, _ = isParsed

    invRow = bsData.get("재고자산", {})
    arRow = bsData.get("매출채권및기타채권", bsData.get("매출채권", {}))
    apRow = bsData.get("매입채무및기타채무", bsData.get("매입채무", {}))
    taRow = bsData.get("자산총계", {})
    revRow = isData.get("매출액", {})
    cogsRow = isData.get("매출원가", {})

    yCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=_MAX_YEARS)
    if len(yCols) < 3:
        return None

    history = []
    for i, col in enumerate(yCols):
        inv = _get(invRow, col)
        ar = _get(arRow, col)
        ap = _get(apRow, col)
        ta = _get(taRow, col)
        rev = _get(revRow, col)
        cogs = _get(cogsRow, col)

        # DSO / DIO
        dso = (ar / rev * 365) if rev > 0 else None
        dio = (inv / cogs * 365) if cogs > 0 else None

        # YoY 성장률
        invGrowth = None
        revGrowth = None
        arGrowth = None
        if i + 1 < len(yCols):
            prevCol = yCols[i + 1]
            prevInv = _get(invRow, prevCol)
            prevRev = _get(revRow, prevCol)
            prevAr = _get(arRow, prevCol)
            if prevInv > 0:
                invGrowth = ((inv - prevInv) / prevInv) * 100
            if prevRev > 0:
                revGrowth = ((rev - prevRev) / prevRev) * 100
            if prevAr > 0:
                arGrowth = ((ar - prevAr) / prevAr) * 100

        divergence = None
        if invGrowth is not None and revGrowth is not None:
            divergence = invGrowth - revGrowth

        arDivergence = None
        if arGrowth is not None and revGrowth is not None:
            arDivergence = arGrowth - revGrowth

        # NOA = (자산 - 현금) - (부채 - 금융부채) ≈ 자산 - 매입채무 - 현금 (간이)
        noa = ta - ap if ta > 0 else None

        history.append(
            {
                "period": col,
                "inventory": inv,
                "receivables": ar,
                "revenue": rev,
                "inventoryGrowth": round(invGrowth, 1) if invGrowth is not None else None,
                "revenueGrowth": round(revGrowth, 1) if revGrowth is not None else None,
                "divergence": round(divergence, 1) if divergence is not None else None,
                "arDivergence": round(arDivergence, 1) if arDivergence is not None else None,
                "dso": round(dso, 1) if dso is not None else None,
                "dio": round(dio, 1) if dio is not None else None,
                "noa": noa,
            }
        )

    if not history:
        return None

    # 재고 신호 판단 (최근 2년)
    recentDiv = [h["divergence"] for h in history[:2] if h["divergence"] is not None]
    if recentDiv:
        avgDiv = sum(recentDiv) / len(recentDiv)
        if avgDiv > 5:
            inventorySignal = "building"
        elif avgDiv < -5:
            inventorySignal = "liquidating"
        else:
            inventorySignal = "stable"
    else:
        inventorySignal = "stable"

    # 매출채권 신호
    recentArDiv = [h["arDivergence"] for h in history[:2] if h["arDivergence"] is not None]
    if recentArDiv:
        avgArDiv = sum(recentArDiv) / len(recentArDiv)
        if avgArDiv > 5:
            receivableSignal = "deteriorating"
        elif avgArDiv < -5:
            receivableSignal = "improving"
        else:
            receivableSignal = "stable"
    else:
        receivableSignal = "stable"

    # NOA 성장률
    noaGrowth = None
    if len(history) >= 2 and history[0]["noa"] and history[1]["noa"] and history[1]["noa"] > 0:
        noaGrowth = ((history[0]["noa"] - history[1]["noa"]) / abs(history[1]["noa"])) * 100

    # 리스크 점수 (0-100)
    riskScore = 30  # 기본
    if inventorySignal == "building":
        riskScore += 25
    if receivableSignal == "deteriorating":
        riskScore += 20
    if noaGrowth is not None and noaGrowth > 20:
        riskScore += 25
    riskScore = min(100, riskScore)

    return {
        "history": history,
        "inventorySignal": inventorySignal,
        "receivableSignal": receivableSignal,
        "noaGrowth": round(noaGrowth, 1) if noaGrowth is not None else None,
        "riskScore": riskScore,
    }


# ══════════════════════════════════════
# calc 9: 동종업계 공시 타이밍
# ══════════════════════════════════════


@memoizedCalc
def calcAnnouncementTiming(company, *, basePeriod: str | None = None) -> dict | None:
    """동종업계 공시 타이밍 — 선발 기업 실적으로 후발 예측.

    같은 업종에서 이미 실적을 발표한 기업들의 성장 방향을 집계한다.
    Ramnath 2002, Thomas & Zhang 2008 — 20년+ 검증된 anomaly.

    Returns
    -------
    dict
        sectorKey : str — 업종 키
        sectorPeersReported : int — 실적 발표 동종 기업 수
        sectorPeersTotal : int — 동종 업종 전체 기업 수
        reportedDirection : dict — 방향별 기업 수 (up, down, flat)
        bellwetherSignal : str — 벨웨더 신호 ("positive" | "negative" | "neutral")
        peerConsensus : float — 피어 합의 점수 (-1.0 ~ +1.0)
        confidence : str — 신뢰도 ("high" | "medium" | "low")
    """
    stockCode = _getStockCode(company)
    if stockCode is None:
        return None

    # 업종 정보
    sectorKey = _getSectorKey(company)
    if sectorKey is None:
        return None

    # scan growth에서 동종 업종 성장률 로드
    try:
        from dartlab.scan import Scan

        scan = Scan()
        growthResult = scan("growth")
        if growthResult is None or not hasattr(growthResult, "df"):
            return None

        df = growthResult.df
    except (ImportError, ValueError, AttributeError):
        return None

    # 업종 필터 (sector 컬럼이 있으면 사용, 없으면 전체)
    sectorCol = None
    for col in ("sector", "industry", "industryGroup", "업종"):
        if col in df.columns:
            sectorCol = col
            break

    if sectorCol:
        peerDf = df.filter(df[sectorCol] == sectorKey)
    else:
        return None

    if peerDf.height < 3:
        return None

    # 성장률 방향 집계
    growthCol = None
    for col in ("revenueGrowth", "revenueCagr3y", "growth", "매출성장률"):
        if col in peerDf.columns:
            growthCol = col
            break

    if growthCol is None:
        return None

    codeCol = "stockCode" if "stockCode" in peerDf.columns else peerDf.columns[0]
    directions = {"up": 0, "down": 0, "flat": 0}
    totalPeers = peerDf.height
    selfExcluded = False

    for row in peerDf.iter_rows(named=True):
        code = str(row.get(codeCol, ""))
        if code == stockCode:
            selfExcluded = True
            continue
        g = row.get(growthCol)
        if g is None:
            continue
        g = float(g)
        if g > 2:
            directions["up"] += 1
        elif g < -2:
            directions["down"] += 1
        else:
            directions["flat"] += 1

    reported = sum(directions.values())
    if reported < 2:
        return None

    # 피어 합의 점수 (-1.0 ~ +1.0)
    peerConsensus = (directions["up"] - directions["down"]) / reported

    # 벨웨더 신호 (다수 방향)
    maxDir = max(directions, key=directions.get)
    if directions[maxDir] / reported >= 0.6:
        bellwetherSignal = "positive" if maxDir == "up" else ("negative" if maxDir == "down" else "neutral")
    else:
        bellwetherSignal = "neutral"

    confidence = "high" if reported >= 5 else ("medium" if reported >= 3 else "low")

    return {
        "sectorKey": sectorKey,
        "sectorPeersReported": reported,
        "sectorPeersTotal": totalPeers - (1 if selfExcluded else 0),
        "reportedDirection": directions,
        "bellwetherSignal": bellwetherSignal,
        "peerConsensus": round(peerConsensus, 3),
        "confidence": confidence,
    }


# ══════════════════════════════════════
# calc 10: 공급망 모멘텀
# ══════════════════════════════════════


@memoizedCalc
def calcSupplyChainSignal(company, *, basePeriod: str | None = None) -> dict | None:
    """공급망 모멘텀 — 관계사 실적이 이 회사를 선행.

    Cohen & Frazzini 2008 (J. Finance) — 고객사 실적이 공급사를 1-2분기 선행.
    DART 투자관계 + 관계사 거래에서 연결 기업을 식별하고,
    상장 관계사의 성장률로 이 회사에 대한 전파 신호를 계산.

    Returns
    -------
    dict
        linkedCompanies : list[dict] — 상장 관계사 목록 (code, name, relationship, revenueGrowth(%))
        networkMomentum : float — 정규화 모멘텀 (-1.0 ~ +1.0)
        nLinkedListed : int — 상장 관계사 수
        supplyChainRisk : str — 공급망 리스크 ("high" | "moderate" | "low")
        confidence : str — 신뢰도 ("high" | "medium" | "low")
    """
    stockCode = _getStockCode(company)
    if stockCode is None:
        return None

    # 관계사 네트워크 추출
    linkedCompanies = _getLinkedCompanies(company, stockCode)
    if not linkedCompanies:
        return None

    # 상장 관계사의 성장률 조회 (scan growth)
    growthMap = _loadGrowthMap()
    if not growthMap:
        return None

    enriched = []
    for lc in linkedCompanies:
        code = lc.get("code", "")
        growth = growthMap.get(code)
        if growth is not None:
            enriched.append(
                {
                    "code": code,
                    "name": lc.get("name", ""),
                    "relationship": lc.get("relationship", ""),
                    "revenueGrowth": round(growth, 1),
                }
            )

    if not enriched:
        return None

    # 가중 평균 모멘텀
    growths = [e["revenueGrowth"] for e in enriched]
    networkMomentum = sum(growths) / len(growths)
    # 정규화 (-1 ~ +1)
    normalizedMomentum = _clamp(networkMomentum / 30)

    # 공급망 리스크
    negCount = sum(1 for g in growths if g < -5)
    if negCount / len(growths) > 0.5:
        supplyChainRisk = "high"
    elif negCount / len(growths) > 0.25:
        supplyChainRisk = "moderate"
    else:
        supplyChainRisk = "low"

    confidence = "high" if len(enriched) >= 5 else ("medium" if len(enriched) >= 2 else "low")

    return {
        "linkedCompanies": enriched[:10],
        "networkMomentum": round(normalizedMomentum, 3),
        "nLinkedListed": len(enriched),
        "supplyChainRisk": supplyChainRisk,
        "confidence": confidence,
    }


def _getLinkedCompanies(company, stockCode: str) -> list[dict]:
    """관계사/투자회사 목록 추출."""
    linked = []

    # 1. 투자관계 (network edges에서)
    try:
        from dartlab.scan.network.edges import buildInvestEdges

        investDf = buildInvestEdges(stockCode)
        if investDf is not None and hasattr(investDf, "height") and investDf.height > 0:
            for row in investDf.iter_rows(named=True):
                toCode = row.get("to_code", "")
                if toCode and row.get("is_listed"):
                    linked.append(
                        {
                            "code": toCode,
                            "name": row.get("to_name", ""),
                            "relationship": "투자",
                        }
                    )
    except (ImportError, ValueError, TypeError):
        pass

    # 2. 관계사 거래 (relatedPartyTx 파이프라인 직접 호출)
    # Company facade namespace 제거(Plan v10 P3) 후 getattr(company, "relatedPartyTx")
    # 는 항상 None 반환하는 dead branch 였음. KRW 6자리 종목에만 호출.
    try:
        stockCode = getattr(company, "stockCode", None)
        if (
            isinstance(stockCode, str)
            and len(stockCode) == 6
            and stockCode.isdigit()
            and getattr(company, "currency", None) == "KRW"
        ):
            accessor = getFinanceDocAccessor()
            rpt = accessor.relatedPartyTx(stockCode) if accessor else None
            if rpt and rpt.revenueTxDf is not None:
                for row in rpt.revenueTxDf.iter_rows(named=True):
                    entity = row.get("entity", "")
                    if entity and entity not in {lc["name"] for lc in linked}:
                        linked.append(
                            {
                                "code": "",
                                "name": entity,
                                "relationship": "거래",
                            }
                        )
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        FileNotFoundError,
        RuntimeError,  # DART 다운로드 실패 (404 등) — mock/신규 종목에서 발생
        OSError,  # 네트워크 단절
    ):
        pass

    return linked


def _loadGrowthMap() -> dict[str, float]:
    """scan growth에서 전종목 매출 성장률 맵을 로드."""
    try:
        from dartlab.scan import Scan

        scan = Scan()
        result = scan("growth")
        if result is None or not hasattr(result, "df"):
            return {}

        df = result.df
        codeCol = "stockCode" if "stockCode" in df.columns else df.columns[0]
        growthCol = None
        for col in ("revenueGrowth", "revenueCagr3y", "growth"):
            if col in df.columns:
                growthCol = col
                break
        if growthCol is None:
            return {}

        gmap = {}
        for row in df.iter_rows(named=True):
            code = str(row.get(codeCol, ""))
            g = row.get(growthCol)
            if code and g is not None:
                gmap[code] = float(g)
        return gmap
    except (ImportError, ValueError, AttributeError):
        return {}


# ══════════════════════════════════════


# 분리된 신호 (BC re-export)
from dartlab.analysis.financial._signalsDirection import (  # noqa: E402, F401
    calcConsensusDirection,
    calcFlowDirection,
    calcRevenueDirection,
)
from dartlab.analysis.financial._signalsEvent import calcEventImpact  # noqa: E402, F401
