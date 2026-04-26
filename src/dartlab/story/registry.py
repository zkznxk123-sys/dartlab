"""story 레지스트리 — 템플릿 기반 Story 생성.

buildBlocks 는 분석 calc* 결과를 블록으로 변환해 BlockMap 으로 반환한다. 100+ 블록을
26+ 그룹으로 묶어 그룹별 빌더 함수로 분리 — 새 블록 추가 시 해당 그룹만 수정.
buildBlocks 본체는 preset 처리 + currency setup + 그룹 loop 만 담당.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from dartlab.story.layout import StoryLayout
from dartlab.story.section import Section
from dartlab.story.templates import TEMPLATE_ORDER, TEMPLATES
from dartlab.story.utils import isTerminal

try:
    import polars as _pl_lib

    _POLARS_ERR: type = _pl_lib.exceptions.PolarsError
except ImportError:
    _POLARS_ERR = RuntimeError

_LOG = logging.getLogger("dartlab.story")

# Phase 4 G15a: buildBlocks preset — 전체 호출 113초/7.9GB 회피
_MINIMAL_KEYS: frozenset[str] = frozenset(
    {
        "profile",
        "segmentComposition",
        "revenueGrowth",
        "marginTrend",
        "cashFlowOverview",
        "cashQuality",
        "leverageTrend",
        "assetStructure",
        "dFV",
        "lifeCycleStage",
        "valuationSins",
    }
)

_STANDARD_KEYS: frozenset[str] = _MINIMAL_KEYS | frozenset(
    {
        "concentration",
        "growthTrend",
        "roicTimeline",
        "distressScore",
        "valuationSynthesis",
        "plausibilityBand",
        # storyPrecedents 제외 (scan 271MB 다운로드 회피 — preset="full" 에서만)
    }
)


def _safeCall(fn: Callable):
    """블록 빌드 실패 시 빈 list 반환 — 한 그룹 실패가 다른 그룹 영향 차단.

    잡는 예외 카테고리:
        KeyError/ValueError/TypeError/AttributeError — 데이터 누락 + 타입 mismatch
        ArithmeticError/IndexError — 계산식 + 인덱싱 실패
        ImportError/RuntimeError — 외부 모듈 + 런타임 의존성 실패
        polars.exceptions.PolarsError — DataFrame 연산 실패
    """
    try:
        return fn()
    except (
        KeyError,
        ValueError,
        TypeError,
        AttributeError,
        ArithmeticError,
        ImportError,
        RuntimeError,
        IndexError,
        _POLARS_ERR,
    ) as exc:
        _LOG.debug(
            "story block build 실패: %s — %s: %s",
            getattr(fn, "__name__", "?"),
            type(exc).__name__,
            exc,
        )
        return []


def _resolvePresetKeys(keys: set[str] | None, preset: str) -> set[str] | None:
    """preset → keys 변환. keys 명시되면 preset 무시.

    minimal (~30초): 6막 골격 블록 ~11개
    standard (기본, ~60초): minimal + 주요 분석 블록 (storyPrecedents 제외)
    full (~113초): 전체 블록 — keys=None 유지
    """
    if keys is not None:
        return keys
    if preset == "minimal":
        return set(_MINIMAL_KEYS)
    if preset == "standard":
        return set(_STANDARD_KEYS)
    return None  # full


def _setupCurrency(company) -> None:
    """story builders + analysis 의 금액 포맷을 company.currency 로 설정.

    contextvars — 스레드 안전. analysis.financial.capital 의 _analysis_currency
    가 없으면 (구버전) silent skip.
    """
    from dartlab.story.builders import _story_currency

    _currency = getattr(company, "currency", "KRW")
    _story_currency.set(_currency)
    try:
        from dartlab.analysis.financial.capital import _analysis_currency

        _analysis_currency.set(_currency)
    except ImportError:
        pass


def _makeNeed(keys: set[str] | None) -> Callable[[str], bool]:
    """need(key) — 그룹 빌더가 사용할 키 게이트 헬퍼."""

    def _need(key: str) -> bool:
        return keys is None or key in keys

    return _need


# ──────────────────────────────────────────────────────────────────
# 그룹 빌더 함수 — buildBlocks 가 호출하는 그룹 단위 책임 분해.
# 각 함수: (company, keys, basePeriod, safe, need, out) -> None.
# 그룹 게이트 (keys 매칭) + lazy import (calc + builder) + 블록 등록.
# ──────────────────────────────────────────────────────────────────


def _buildRevenueBlocks(company, keys, basePeriod, safe: Callable, need: Callable, out: dict) -> None:
    """1 부 — 사업구조 (10 블록)."""
    if keys is not None and not (
        keys
        & {
            "profile",
            "segmentComposition",
            "segmentTrend",
            "region",
            "product",
            "growth",
            "concentration",
            "revenueQuality",
            "growthContribution",
            "revenueFlags",
        }
    ):
        return
    from dartlab.analysis.financial.revenue import (
        calcBreakdown,
        calcCompanyProfile,
        calcConcentration,
        calcFlags,
        calcGrowthContribution,
        calcRevenueGrowth,
        calcRevenueQuality,
        calcSegmentComposition,
        calcSegmentTrend,
    )
    from dartlab.story.builders import (
        breakdownBlock,
        concentrationBlock,
        growthContributionBlock,
        profileBlock,
        revenueFlagsBlock,
        revenueGrowthBlock,
        revenueQualityBlock,
        segmentCompositionBlock,
        segmentTrendBlock,
    )

    if need("profile"):
        out["profile"] = safe(lambda: profileBlock(calcCompanyProfile(company, basePeriod=basePeriod)))
    if need("segmentComposition"):
        out["segmentComposition"] = safe(
            lambda: segmentCompositionBlock(calcSegmentComposition(company, basePeriod=basePeriod))
        )
    if need("segmentTrend"):
        out["segmentTrend"] = safe(lambda: segmentTrendBlock(calcSegmentTrend(company, basePeriod=basePeriod)))
    if need("region"):
        out["region"] = safe(lambda: breakdownBlock(calcBreakdown(company, "region", basePeriod=basePeriod), "region"))
    if need("product"):
        out["product"] = safe(
            lambda: breakdownBlock(calcBreakdown(company, "product", basePeriod=basePeriod), "product")
        )
    if need("growth"):
        out["growth"] = safe(lambda: revenueGrowthBlock(calcRevenueGrowth(company, basePeriod=basePeriod)))
    if need("concentration"):
        out["concentration"] = safe(lambda: concentrationBlock(calcConcentration(company, basePeriod=basePeriod)))
    if need("revenueQuality"):
        out["revenueQuality"] = safe(lambda: revenueQualityBlock(calcRevenueQuality(company, basePeriod=basePeriod)))
    if need("growthContribution"):
        out["growthContribution"] = safe(
            lambda: growthContributionBlock(calcGrowthContribution(company, basePeriod=basePeriod))
        )
    if need("revenueFlags"):
        out["revenueFlags"] = safe(lambda: revenueFlagsBlock(calcFlags(company, basePeriod=basePeriod)))


def _buildCapitalBlocks(company, keys, basePeriod, safe: Callable, need: Callable, out: dict) -> None:
    """1 부 — 자본구조 (9 블록)."""
    if keys is not None and not (
        keys
        & {
            "fundingSources",
            "capitalOverview",
            "capitalTimeline",
            "debtTimeline",
            "interestBurden",
            "liquidity",
            "cashFlowStructure",
            "distressIndicators",
            "capitalFlags",
        }
    ):
        return
    from dartlab.analysis.financial.capital import (
        calcCapitalFlags,
        calcCapitalOverview,
        calcCapitalTimeline,
        calcCashFlowStructure,
        calcDebtTimeline,
        calcDistressIndicators,
        calcFundingSources,
        calcInterestBurden,
        calcLiquidity,
    )
    from dartlab.story.builders import (
        capitalFlagsBlock,
        capitalOverviewBlock,
        capitalTimelineBlock,
        cashFlowBlock,
        debtTimelineBlock,
        distressBlock,
        fundingSourcesBlock,
        interestBurdenBlock,
        liquidityBlock,
    )

    if need("fundingSources"):
        out["fundingSources"] = safe(lambda: fundingSourcesBlock(calcFundingSources(company, basePeriod=basePeriod)))
    if need("capitalOverview"):
        out["capitalOverview"] = safe(lambda: capitalOverviewBlock(calcCapitalOverview(company, basePeriod=basePeriod)))
    if need("capitalTimeline"):
        out["capitalTimeline"] = safe(lambda: capitalTimelineBlock(calcCapitalTimeline(company, basePeriod=basePeriod)))
    if need("debtTimeline"):
        out["debtTimeline"] = safe(lambda: debtTimelineBlock(calcDebtTimeline(company, basePeriod=basePeriod)))
    if need("interestBurden"):
        out["interestBurden"] = safe(lambda: interestBurdenBlock(calcInterestBurden(company, basePeriod=basePeriod)))
    if need("liquidity"):
        out["liquidity"] = safe(lambda: liquidityBlock(calcLiquidity(company, basePeriod=basePeriod)))
    if need("cashFlowStructure"):
        out["cashFlowStructure"] = safe(lambda: cashFlowBlock(calcCashFlowStructure(company, basePeriod=basePeriod)))
    if need("distressIndicators"):
        out["distressIndicators"] = safe(lambda: distressBlock(calcDistressIndicators(company, basePeriod=basePeriod)))
    if need("capitalFlags"):
        out["capitalFlags"] = safe(lambda: capitalFlagsBlock(calcCapitalFlags(company, basePeriod=basePeriod)))


def _buildAssetBlocks(company, keys, basePeriod, safe: Callable, need: Callable, out: dict) -> None:
    """1 부 — 자산구조 (4 블록)."""
    if keys is not None and not (keys & {"assetStructure", "workingCapital", "capexPattern", "assetFlags"}):
        return
    from dartlab.analysis.financial.asset import (
        calcAssetFlags,
        calcAssetStructure,
        calcCapexPattern,
        calcWorkingCapital,
    )
    from dartlab.story.builders import (
        assetFlagsBlock,
        assetStructureBlock,
        capexBlock,
        workingCapitalBlock,
    )

    if need("assetStructure"):
        out["assetStructure"] = safe(lambda: assetStructureBlock(calcAssetStructure(company, basePeriod=basePeriod)))
    if need("workingCapital"):
        out["workingCapital"] = safe(lambda: workingCapitalBlock(calcWorkingCapital(company, basePeriod=basePeriod)))
    if need("capexPattern"):
        out["capexPattern"] = safe(lambda: capexBlock(calcCapexPattern(company, basePeriod=basePeriod)))
    if need("assetFlags"):
        out["assetFlags"] = safe(lambda: assetFlagsBlock(calcAssetFlags(company, basePeriod=basePeriod)))


def _buildCashflowBlocks(company, keys, basePeriod, safe: Callable, need: Callable, out: dict) -> None:
    """1 부 — 현금흐름 (4 블록)."""
    if keys is not None and not (keys & {"cashFlowOverview", "cashQuality", "ocfDecomposition", "cashFlowFlags"}):
        return
    from dartlab.analysis.financial.cashflow import (
        calcCashFlowFlags,
        calcCashFlowOverview,
        calcCashQuality,
        calcOcfDecomposition,
    )
    from dartlab.story.builders import (
        cashFlowFlagsBlock,
        cashFlowOverviewBlock,
        cashQualityBlock,
        ocfDecompositionBlock,
    )

    if need("cashFlowOverview"):
        out["cashFlowOverview"] = safe(
            lambda: cashFlowOverviewBlock(calcCashFlowOverview(company, basePeriod=basePeriod))
        )
    if need("cashQuality"):
        out["cashQuality"] = safe(lambda: cashQualityBlock(calcCashQuality(company, basePeriod=basePeriod)))
    if need("ocfDecomposition"):
        out["ocfDecomposition"] = safe(
            lambda: ocfDecompositionBlock(calcOcfDecomposition(company, basePeriod=basePeriod))
        )
    if need("cashFlowFlags"):
        out["cashFlowFlags"] = safe(lambda: cashFlowFlagsBlock(calcCashFlowFlags(company, basePeriod=basePeriod)))


def buildBlocks(
    company,
    keys: set[str] | None = None,
    *,
    basePeriod: str | None = None,
    preset: str = "standard",
):
    """블록 사전 — analysis calc* 결과를 블록으로 변환.

    keys 가 지정되면 해당 블록만 빌드한다 (선택적 빌드, preset 무시).
    keys=None 이면 preset 에 따라 빌드 범위 결정 — 자세한 정책은
    ``_resolvePresetKeys`` 참조.

    내부적으로 ``_GROUP_BUILDERS`` (그룹별 빌더 list) 를 순회. 새 블록 추가 시
    해당 그룹 빌더 함수만 수정 + (필요 시) 새 그룹 빌더 등록.
    """
    keys = _resolvePresetKeys(keys, preset)
    _setupCurrency(company)
    # buildBlocks 본체에서 사용하는 헬퍼 — 그룹 빌더 추출 시 인자로 전달.
    # 이전 inline 정의 (_safe/_need) 와 같은 이름 유지해 본체 호출 그대로.
    _safe = _safeCall
    _need = _makeNeed(keys)
    b: dict = {}

    # ── 1부: 사업구조 + 자본구조 + 자산구조 + 현금흐름 ──
    _buildRevenueBlocks(company, keys, basePeriod, _safe, _need, b)
    _buildCapitalBlocks(company, keys, basePeriod, _safe, _need, b)
    _buildAssetBlocks(company, keys, basePeriod, _safe, _need, b)
    _buildCashflowBlocks(company, keys, basePeriod, _safe, _need, b)

    # ── 2부: 재무비율 분석 ──
    if keys is None or keys & {
        "marginTrend",
        "returnTrend",
        "dupont",
        "penmanDecomposition",
        "roicTree",
        "profitabilityFlags",
    }:
        from dartlab.analysis.financial.profitability import (
            calcMarginTrend,
            calcPenmanDecomposition,
            calcProfitabilityFlags,
            calcReturnTrend,
            calcRoicTree,
        )
        from dartlab.story.builders import (
            dupontBlock,
            marginTrendBlock,
            penmanDecompositionBlock,
            profitabilityFlagsBlock,
            returnTrendBlock,
            roicTreeBlock,
        )

        if _need("marginTrend"):
            b["marginTrend"] = _safe(lambda: marginTrendBlock(calcMarginTrend(company, basePeriod=basePeriod)))
        if _need("returnTrend"):
            b["returnTrend"] = _safe(lambda: returnTrendBlock(calcReturnTrend(company, basePeriod=basePeriod)))
        if _need("dupont"):
            b["dupont"] = _safe(lambda: dupontBlock(calcReturnTrend(company, basePeriod=basePeriod)))
        if _need("penmanDecomposition"):
            b["penmanDecomposition"] = _safe(
                lambda: penmanDecompositionBlock(calcPenmanDecomposition(company, basePeriod=basePeriod))
            )
        if _need("roicTree"):
            b["roicTree"] = _safe(lambda: roicTreeBlock(calcRoicTree(company, basePeriod=basePeriod)))
        if _need("profitabilityFlags"):
            b["profitabilityFlags"] = _safe(
                lambda: profitabilityFlagsBlock(calcProfitabilityFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {"growthTrend", "growthQuality", "cagrComparison", "growthFlags"}:
        from dartlab.analysis.financial.growthAnalysis import (
            calcCagrComparison,
            calcGrowthFlags,
            calcGrowthQuality,
            calcGrowthTrend,
        )
        from dartlab.story.builders import (
            cagrComparisonBlock,
            growthFlagsBlock,
            growthQualityBlock,
            growthTrendBlock,
        )

        if _need("growthTrend"):
            b["growthTrend"] = _safe(lambda: growthTrendBlock(calcGrowthTrend(company, basePeriod=basePeriod)))
        if _need("growthQuality"):
            b["growthQuality"] = _safe(lambda: growthQualityBlock(calcGrowthQuality(company, basePeriod=basePeriod)))
        if _need("cagrComparison"):
            b["cagrComparison"] = _safe(lambda: cagrComparisonBlock(calcCagrComparison(company, basePeriod=basePeriod)))
        if _need("growthFlags"):
            b["growthFlags"] = _safe(lambda: growthFlagsBlock(calcGrowthFlags(company, basePeriod=basePeriod)))

    if keys is None or keys & {
        "leverageTrend",
        "coverageTrend",
        "distressScore",
        "stabilityFlags",
        "marketRisk",
        "scenarioSensitivity",
        "criticalAssumptions",
    }:
        from dartlab.analysis.financial.stability import (
            calcCoverageTrend,
            calcDistressScore,
            calcLeverageTrend,
            calcStabilityFlags,
        )
        from dartlab.story.builders import (
            coverageTrendBlock,
            distressScoreBlock,
            leverageTrendBlock,
            stabilityFlagsBlock,
        )

        if _need("leverageTrend"):
            b["leverageTrend"] = _safe(lambda: leverageTrendBlock(calcLeverageTrend(company, basePeriod=basePeriod)))
        if _need("coverageTrend"):
            b["coverageTrend"] = _safe(lambda: coverageTrendBlock(calcCoverageTrend(company, basePeriod=basePeriod)))
        if _need("distressScore"):
            b["distressScore"] = _safe(lambda: distressScoreBlock(calcDistressScore(company, basePeriod=basePeriod)))
        if _need("stabilityFlags"):
            b["stabilityFlags"] = _safe(lambda: stabilityFlagsBlock(calcStabilityFlags(company, basePeriod=basePeriod)))
        if _need("scenarioSensitivity") or _need("criticalAssumptions"):
            from dartlab.analysis.financial.scenarioSensitivity import calcScenarioSensitivity
            from dartlab.story.builders import criticalAssumptionsBlock, scenarioSensitivityBlock

            _ss = _safe(lambda: calcScenarioSensitivity(company, basePeriod=basePeriod))
            if _need("scenarioSensitivity"):
                b["scenarioSensitivity"] = _safe(lambda: scenarioSensitivityBlock(_ss))
            if _need("criticalAssumptions"):
                b["criticalAssumptions"] = _safe(lambda: criticalAssumptionsBlock(_ss))
            # improvementLevers를 여기서 즉시 계산 (같은 SS 캐시 시점, 메모리 압박 전)
            if _need("improvementLevers") and _ss:
                from dartlab.analysis.financial.scenarioSensitivity import calcImprovementLevers
                from dartlab.story.builders import improvementLeversBlock

                try:
                    _il_data = calcImprovementLevers(company, basePeriod=basePeriod)
                    b["improvementLevers"] = improvementLeversBlock(_il_data) if _il_data else []
                except Exception as _e:
                    import logging

                    logging.getLogger("dartlab.story").debug("improvementLevers: %s", _e)
                    b["improvementLevers"] = []
        if _need("marketRisk"):
            from dartlab.quant.extended import calcMarketRisk
            from dartlab.story.builders import marketRiskBlock

            b["marketRisk"] = _safe(lambda: marketRiskBlock(calcMarketRisk(company)))

    if keys is None or keys & {"turnoverTrend", "cccTrend", "efficiencyFlags"}:
        from dartlab.analysis.financial.efficiency import (
            calcEfficiencyFlags,
            calcTurnoverTrend,
        )
        from dartlab.story.builders import (
            cccTrendBlock,
            efficiencyFlagsBlock,
            turnoverTrendBlock,
        )

        if _need("turnoverTrend"):
            b["turnoverTrend"] = _safe(lambda: turnoverTrendBlock(calcTurnoverTrend(company, basePeriod=basePeriod)))
        if _need("cccTrend"):
            b["cccTrend"] = _safe(lambda: cccTrendBlock(calcTurnoverTrend(company, basePeriod=basePeriod)))
        if _need("efficiencyFlags"):
            b["efficiencyFlags"] = _safe(
                lambda: efficiencyFlagsBlock(calcEfficiencyFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {"scorecard", "piotroski", "summaryFlags"}:
        from dartlab.analysis.financial.scorecard import (
            calcPiotroskiDetail,
            calcScorecard,
            calcSummaryFlags,
        )
        from dartlab.story.builders import (
            piotroskiBlock,
            scorecardBlock,
            summaryFlagsBlock,
        )

        if _need("scorecard"):
            b["scorecard"] = _safe(lambda: scorecardBlock(calcScorecard(company, basePeriod=basePeriod)))
        if _need("piotroski"):
            b["piotroski"] = _safe(lambda: piotroskiBlock(calcPiotroskiDetail(company, basePeriod=basePeriod)))
        if _need("summaryFlags"):
            b["summaryFlags"] = _safe(lambda: summaryFlagsBlock(calcSummaryFlags(company, basePeriod=basePeriod)))

    # ── 업종별 KPI (독립 조건) ──
    if keys is None or keys & {"sectorKpi"}:
        if _need("sectorKpi"):
            from dartlab.analysis.financial.sectorKpi import sectorKpi as _sectorKpi
            from dartlab.story.builders import sectorKpiBlock

            b["sectorKpi"] = _safe(lambda: sectorKpiBlock(_sectorKpi(company)))

    # ── 산업 밸류체인 (L2 industry 엔진) ──
    if keys is None or keys & {"chainPosition", "sectorMetrics", "sectorOutlook"}:
        from dartlab.industry.calcs import calcChainPosition, calcSectorCycle, calcSectorDynamics, calcSectorMetrics
        from dartlab.story.builders import chainPositionBlock, sectorMetricsBlock, sectorOutlookBlock

        if _need("chainPosition"):
            b["chainPosition"] = _safe(lambda: chainPositionBlock(calcChainPosition(company)))
        if _need("sectorMetrics"):
            b["sectorMetrics"] = _safe(lambda: sectorMetricsBlock(calcSectorMetrics(company)))
        if _need("sectorOutlook"):
            b["sectorOutlook"] = _safe(
                lambda: sectorOutlookBlock(calcSectorCycle(company), calcSectorDynamics(company))
            )

    # ── 3부: 심화 분석 ──
    if keys is None or keys & {
        "accrualAnalysis",
        "earningsPersistence",
        "beneishMScore",
        "richardsonAccrual",
        "nonOperatingBreakdown",
        "earningsQualityFlags",
    }:
        from dartlab.analysis.financial.earningsQuality import (
            calcAccrualAnalysis,
            calcBeneishTimeline,
            calcEarningsPersistence,
            calcEarningsQualityFlags,
            calcNonOperatingBreakdown,
            calcRichardsonAccrual,
        )
        from dartlab.story.builders import (
            accrualAnalysisBlock,
            beneishMScoreBlock,
            earningsPersistenceBlock,
            earningsQualityFlagsBlock,
            nonOperatingBreakdownBlock,
            richardsonAccrualBlock,
        )

        if _need("accrualAnalysis"):
            b["accrualAnalysis"] = _safe(
                lambda: accrualAnalysisBlock(calcAccrualAnalysis(company, basePeriod=basePeriod))
            )
        if _need("earningsPersistence"):
            b["earningsPersistence"] = _safe(
                lambda: earningsPersistenceBlock(calcEarningsPersistence(company, basePeriod=basePeriod))
            )
        if _need("beneishMScore"):
            b["beneishMScore"] = _safe(lambda: beneishMScoreBlock(calcBeneishTimeline(company, basePeriod=basePeriod)))
        if _need("richardsonAccrual"):
            b["richardsonAccrual"] = _safe(
                lambda: richardsonAccrualBlock(calcRichardsonAccrual(company, basePeriod=basePeriod))
            )
        if _need("nonOperatingBreakdown"):
            b["nonOperatingBreakdown"] = _safe(
                lambda: nonOperatingBreakdownBlock(calcNonOperatingBreakdown(company, basePeriod=basePeriod))
            )
        if _need("earningsQualityFlags"):
            b["earningsQualityFlags"] = _safe(
                lambda: earningsQualityFlagsBlock(calcEarningsQualityFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {"costBreakdown", "operatingLeverage", "breakevenEstimate", "costStructureFlags"}:
        from dartlab.analysis.financial.costStructure import (
            calcBreakevenEstimate,
            calcCostBreakdown,
            calcCostStructureFlags,
            calcOperatingLeverage,
        )
        from dartlab.story.builders import (
            breakevenEstimateBlock,
            costBreakdownBlock,
            costStructureFlagsBlock,
            operatingLeverageBlock,
        )

        if _need("costBreakdown"):
            b["costBreakdown"] = _safe(lambda: costBreakdownBlock(calcCostBreakdown(company, basePeriod=basePeriod)))
        if _need("operatingLeverage"):
            b["operatingLeverage"] = _safe(
                lambda: operatingLeverageBlock(calcOperatingLeverage(company, basePeriod=basePeriod))
            )
        if _need("breakevenEstimate"):
            b["breakevenEstimate"] = _safe(
                lambda: breakevenEstimateBlock(calcBreakevenEstimate(company, basePeriod=basePeriod))
            )
        if _need("costStructureFlags"):
            b["costStructureFlags"] = _safe(
                lambda: costStructureFlagsBlock(calcCostStructureFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {
        "dividendPolicy",
        "shareholderReturn",
        "reinvestment",
        "fcfUsage",
        "capitalAllocationFlags",
    }:
        from dartlab.analysis.financial.capitalAllocation import (
            calcCapitalAllocationFlags,
            calcDividendPolicy,
            calcFcfUsage,
            calcReinvestment,
            calcShareholderReturn,
            calcTreasuryStockStatus,
        )
        from dartlab.story.builders import (
            capitalAllocationFlagsBlock,
            dividendPolicyBlock,
            dividendSustainabilityBlock,
            fcfUsageBlock,
            reinvestmentBlock,
            shareholderReturnBlock,
            totalShareholderReturnBlock,
            treasuryStockStatusBlock,
        )

        _divCache: dict = {}
        _shCache: dict = {}

        def _getDiv():
            if "v" not in _divCache:
                _divCache["v"] = calcDividendPolicy(company, basePeriod=basePeriod)
            return _divCache["v"]

        def _getSh():
            if "v" not in _shCache:
                _shCache["v"] = calcShareholderReturn(company, basePeriod=basePeriod)
            return _shCache["v"]

        if _need("dividendPolicy"):
            b["dividendPolicy"] = _safe(lambda: dividendPolicyBlock(_getDiv()))
        if _need("shareholderReturn"):
            b["shareholderReturn"] = _safe(lambda: shareholderReturnBlock(_getSh()))
        if _need("reinvestment"):
            b["reinvestment"] = _safe(lambda: reinvestmentBlock(calcReinvestment(company, basePeriod=basePeriod)))
        if _need("fcfUsage"):
            b["fcfUsage"] = _safe(lambda: fcfUsageBlock(calcFcfUsage(company, basePeriod=basePeriod)))
        if _need("dividendSustainability"):
            b["dividendSustainability"] = _safe(lambda: dividendSustainabilityBlock(_getDiv(), _getSh()))
        if _need("totalShareholderReturn"):
            b["totalShareholderReturn"] = _safe(lambda: totalShareholderReturnBlock(_getSh()))
        if _need("treasuryStockStatus"):
            b["treasuryStockStatus"] = _safe(
                lambda: treasuryStockStatusBlock(calcTreasuryStockStatus(company, basePeriod=basePeriod))
            )
        if _need("capitalAllocationFlags"):
            b["capitalAllocationFlags"] = _safe(
                lambda: capitalAllocationFlagsBlock(calcCapitalAllocationFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {"roicTimeline", "investmentIntensity", "evaTimeline", "investmentFlags"}:
        from dartlab.analysis.financial.investmentAnalysis import (
            calcEvaTimeline,
            calcInvestmentFlags,
            calcInvestmentIntensity,
            calcRoicTimeline,
        )
        from dartlab.story.builders import (
            evaTimelineBlock,
            investmentFlagsBlock,
            investmentIntensityBlock,
            roicTimelineBlock,
        )

        if _need("roicTimeline"):
            b["roicTimeline"] = _safe(lambda: roicTimelineBlock(calcRoicTimeline(company, basePeriod=basePeriod)))
        if _need("investmentIntensity"):
            b["investmentIntensity"] = _safe(
                lambda: investmentIntensityBlock(calcInvestmentIntensity(company, basePeriod=basePeriod))
            )
        if _need("evaTimeline"):
            b["evaTimeline"] = _safe(lambda: evaTimelineBlock(calcEvaTimeline(company, basePeriod=basePeriod)))
        if _need("investmentFlags"):
            b["investmentFlags"] = _safe(
                lambda: investmentFlagsBlock(calcInvestmentFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {
        "isCfDivergence",
        "isBsDivergence",
        "anomalyScore",
        "articulationCheck",
        "effectiveTaxRate",
        "deferredTax",
        "crossStatementFlags",
    }:
        from dartlab.analysis.financial.crossStatement import (
            calcAnomalyScore,
            calcArticulationCheck,
            calcCrossStatementFlags,
            calcIsBsDivergence,
            calcIsCfDivergence,
        )
        from dartlab.analysis.financial.taxAnalysis import (
            calcDeferredTax,
            calcEffectiveTaxRate,
            calcTaxFlags,
        )
        from dartlab.story.builders import (
            anomalyScoreBlock,
            articulationCheckBlock,
            crossStatementFlagsBlock,
            deferredTaxBlock,
            effectiveTaxRateBlock,
            isBsDivergenceBlock,
            isCfDivergenceBlock,
        )

        if _need("isCfDivergence"):
            b["isCfDivergence"] = _safe(lambda: isCfDivergenceBlock(calcIsCfDivergence(company, basePeriod=basePeriod)))
        if _need("isBsDivergence"):
            b["isBsDivergence"] = _safe(lambda: isBsDivergenceBlock(calcIsBsDivergence(company, basePeriod=basePeriod)))
        if _need("anomalyScore"):
            b["anomalyScore"] = _safe(lambda: anomalyScoreBlock(calcAnomalyScore(company, basePeriod=basePeriod)))
        if _need("articulationCheck"):
            b["articulationCheck"] = _safe(
                lambda: articulationCheckBlock(calcArticulationCheck(company, basePeriod=basePeriod))
            )
        if _need("effectiveTaxRate"):
            b["effectiveTaxRate"] = _safe(
                lambda: effectiveTaxRateBlock(calcEffectiveTaxRate(company, basePeriod=basePeriod))
            )
        if _need("deferredTax"):
            b["deferredTax"] = _safe(lambda: deferredTaxBlock(calcDeferredTax(company, basePeriod=basePeriod)))
        if _need("crossStatementFlags"):
            b["crossStatementFlags"] = _safe(
                lambda: crossStatementFlagsBlock(
                    calcCrossStatementFlags(company, basePeriod=basePeriod)
                    + calcTaxFlags(company, basePeriod=basePeriod)
                )
            )

    # ── 3-6: 신용평가 ──
    if keys is None or keys & {
        "creditMetrics",
        "creditScore",
        "creditHistory",
        "cashFlowGrade",
        "creditPeerPosition",
        "creditFlags",
        "creditNarrative",
        "creditAudit",
    }:
        from dartlab.credit.calcs import (
            calcCashFlowGrade,
            calcCreditAudit,
            calcCreditFlags,
            calcCreditHistory,
            calcCreditMetrics,
            calcCreditNarrative,
            calcCreditPeerPosition,
            calcCreditScore,
        )
        from dartlab.story.builders import (
            cashFlowGradeBlock,
            creditAuditBlock,
            creditFlagsBlock,
            creditHistoryBlock,
            creditMetricsBlock,
            creditNarrativeBlock,
            creditPeerPositionBlock,
            creditScoreBlock,
        )

        if _need("creditMetrics"):
            b["creditMetrics"] = _safe(lambda: creditMetricsBlock(calcCreditMetrics(company, basePeriod=basePeriod)))
        if _need("creditScore"):
            b["creditScore"] = _safe(lambda: creditScoreBlock(calcCreditScore(company, basePeriod=basePeriod)))
        if _need("creditHistory"):
            b["creditHistory"] = _safe(lambda: creditHistoryBlock(calcCreditHistory(company, basePeriod=basePeriod)))
        if _need("cashFlowGrade"):
            b["cashFlowGrade"] = _safe(lambda: cashFlowGradeBlock(calcCashFlowGrade(company, basePeriod=basePeriod)))
        if _need("creditPeerPosition"):
            b["creditPeerPosition"] = _safe(
                lambda: creditPeerPositionBlock(calcCreditPeerPosition(company, basePeriod=basePeriod))
            )
        if _need("creditFlags"):
            b["creditFlags"] = _safe(lambda: creditFlagsBlock(calcCreditFlags(company, basePeriod=basePeriod)))
        if _need("creditNarrative"):
            b["creditNarrative"] = _safe(
                lambda: creditNarrativeBlock(calcCreditNarrative(company, basePeriod=basePeriod))
            )
        if _need("creditAudit"):
            b["creditAudit"] = _safe(lambda: creditAuditBlock(calcCreditAudit(company, basePeriod=basePeriod)))
        if _need("creditScenario"):
            from dartlab.story.builders import creditScenarioBlock

            _base_credit = b.get("creditScore")
            _stress_overrides = {"debtRatio": 80.0, "interestCoverage": 2.0}
            _stress_credit = _safe(lambda: calcCreditScore(company, basePeriod=basePeriod, overrides=_stress_overrides))
            if _base_credit and _stress_credit:
                # creditScoreBlock 결과에서 원본 dict 추출
                _base_data = calcCreditScore(company, basePeriod=basePeriod)
                _stress_data = calcCreditScore(company, basePeriod=basePeriod, overrides=_stress_overrides)
                b["creditScenario"] = _safe(lambda: creditScenarioBlock(_base_data, _stress_data, _stress_overrides))

    # ── 4부: 가치평가 ──
    if keys is None or keys & {
        "dcfValuation",
        "ddmValuation",
        "relativeValuation",
        "residualIncome",
        "priceTarget",
        "reverseImplied",
        "sensitivity",
        "valuationSynthesis",
        "valuationFlags",
        "lifeCycleStage",
        "valuationSins",
        "dFV",
    }:
        from dartlab.analysis.financial.valuation import (
            calcDcf,
            calcDdm,
            calcPriceTarget,
            calcReverseImplied,
            calcSensitivity,
            calcValuationFlags,
            calcValuationSynthesis,
        )
        from dartlab.analysis.financial.valuation import (
            calcRelativeValuation as calcRelVal,
        )
        from dartlab.analysis.financial.valuation import (
            calcResidualIncome as calcRim,
        )
        from dartlab.story.builders import (
            dcfValuationBlock,
            ddmValuationBlock,
            priceTargetBlock,
            relativeValuationBlock,
            residualIncomeBlock,
            reverseImpliedBlock,
            sensitivityBlock,
            valuationFlagsBlock,
            valuationSynthesisBlock,
        )

        if _need("dcfValuation"):
            b["dcfValuation"] = _safe(lambda: dcfValuationBlock(calcDcf(company, basePeriod=basePeriod)))
        if _need("ddmValuation"):
            b["ddmValuation"] = _safe(lambda: ddmValuationBlock(calcDdm(company, basePeriod=basePeriod)))
        if _need("relativeValuation"):
            b["relativeValuation"] = _safe(lambda: relativeValuationBlock(calcRelVal(company, basePeriod=basePeriod)))
        if _need("residualIncome"):
            b["residualIncome"] = _safe(lambda: residualIncomeBlock(calcRim(company, basePeriod=basePeriod)))
        # priceTarget 결과를 valuationSynthesis 에 전달 — 두 모델 차이 narration 자동 추가
        _ptCache: dict = {}

        def _getPt():
            if "v" not in _ptCache:
                _ptCache["v"] = calcPriceTarget(company, basePeriod=basePeriod)
            return _ptCache["v"]

        if _need("priceTarget"):
            b["priceTarget"] = _safe(lambda: priceTargetBlock(_getPt()))
        if _need("reverseImplied"):
            b["reverseImplied"] = _safe(lambda: reverseImpliedBlock(calcReverseImplied(company, basePeriod=basePeriod)))
        if _need("sensitivity"):
            b["sensitivity"] = _safe(lambda: sensitivityBlock(calcSensitivity(company, basePeriod=basePeriod)))
        if _need("valuationSynthesis"):
            b["valuationSynthesis"] = _safe(
                lambda: valuationSynthesisBlock(
                    calcValuationSynthesis(company, basePeriod=basePeriod),
                    priceTargetData=_getPt(),
                )
            )
        if _need("valuationFlags"):
            b["valuationFlags"] = _safe(lambda: valuationFlagsBlock(calcValuationFlags(company, basePeriod=basePeriod)))
        # dFV (dartlab Fair Value) — 4엔진 통합 적정주가
        if _need("dFV") or _need("methodFitness") or _need("qualityFactors"):
            from dartlab.analysis.valuation.dFV import calcDFV
            from dartlab.story.builders import dFVBlock, methodFitnessBlock, qualityFactorsBlock

            _dfv_data = _safe(lambda: calcDFV(company, basePeriod=basePeriod))
            if _need("dFV"):
                b["dFV"] = dFVBlock(_dfv_data) if _dfv_data else []
            if _need("methodFitness"):
                b["methodFitness"] = methodFitnessBlock(_dfv_data) if _dfv_data else []
            if _need("qualityFactors"):
                b["qualityFactors"] = qualityFactorsBlock(_dfv_data) if _dfv_data else []

        # Damodaran 흡수 — lifeCycle / valuationSins
        if _need("lifeCycleStage"):
            from dartlab.analysis.financial.lifeCycle import calcLifeCycle
            from dartlab.story.builders import lifeCycleStageBlock

            b["lifeCycleStage"] = _safe(lambda: lifeCycleStageBlock(calcLifeCycle(company, basePeriod=basePeriod)))
        if _need("valuationSins"):
            from dartlab.analysis.financial.storyValidation import calcValuationSins
            from dartlab.story.builders import valuationSinsBlock

            b["valuationSins"] = _safe(lambda: valuationSinsBlock(calcValuationSins(company, basePeriod=basePeriod)))

    # ── Damodaran 흡수 — 수익구조 storyPrecedents ──
    if keys is None or "storyPrecedents" in keys:
        from dartlab.analysis.financial.storyValidation import calcStoryPrecedents
        from dartlab.story.builders import storyPrecedentsBlock

        if _need("storyPrecedents"):
            b["storyPrecedents"] = _safe(
                lambda: storyPrecedentsBlock(calcStoryPrecedents(company, basePeriod=basePeriod))
            )

    # ── Damodaran 흡수 — 매출전망 plausibilityBand ──
    if keys is None or "plausibilityBand" in keys:
        from dartlab.analysis.financial.storyValidation import calcPlausibilityBand
        from dartlab.story.builders import plausibilityBandBlock

        if _need("plausibilityBand"):
            b["plausibilityBand"] = _safe(
                lambda: plausibilityBandBlock(calcPlausibilityBand(company, basePeriod=basePeriod))
            )

    # ── 5부: 비재무 심화 ──
    if keys is None or keys & {
        "ownershipTrend",
        "boardComposition",
        "auditOpinionTrend",
        "governanceFlags",
        "executivePayDivergence",
        "independentDirectorQuality",
    }:
        from dartlab.analysis.financial.governance import (
            calcAuditOpinionTrend,
            calcBoardComposition,
            calcExecutivePayDivergence,
            calcGovernanceFlags,
            calcIndependentDirectorQuality,
            calcOwnershipTrend,
        )
        from dartlab.story.builders import (
            auditOpinionTrendBlock,
            boardCompositionBlock,
            executivePayDivergenceBlock,
            governanceFlagsBlock,
            independentDirectorQualityBlock,
            ownershipTrendBlock,
        )

        if _need("ownershipTrend"):
            b["ownershipTrend"] = _safe(lambda: ownershipTrendBlock(calcOwnershipTrend(company, basePeriod=basePeriod)))
        if _need("boardComposition"):
            b["boardComposition"] = _safe(
                lambda: boardCompositionBlock(calcBoardComposition(company, basePeriod=basePeriod))
            )
        if _need("auditOpinionTrend"):
            b["auditOpinionTrend"] = _safe(
                lambda: auditOpinionTrendBlock(calcAuditOpinionTrend(company, basePeriod=basePeriod))
            )
        if _need("executivePayDivergence"):
            b["executivePayDivergence"] = _safe(
                lambda: executivePayDivergenceBlock(calcExecutivePayDivergence(company, basePeriod=basePeriod))
            )
        if _need("independentDirectorQuality"):
            b["independentDirectorQuality"] = _safe(
                lambda: independentDirectorQualityBlock(calcIndependentDirectorQuality(company, basePeriod=basePeriod))
            )
        if _need("governanceFlags"):
            b["governanceFlags"] = _safe(
                lambda: governanceFlagsBlock(calcGovernanceFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {
        "disclosureChangeSummary",
        "keyTopicChanges",
        "changeIntensity",
        "disclosureDeltaFlags",
    }:
        from dartlab.analysis.financial.disclosureDelta import (
            calcChangeIntensity,
            calcDisclosureChangeSummary,
            calcDisclosureDeltaFlags,
            calcKeyTopicChanges,
        )
        from dartlab.story.builders import (
            changeIntensityBlock,
            disclosureChangeSummaryBlock,
            disclosureDeltaFlagsBlock,
            keyTopicChangesBlock,
        )

        if _need("disclosureChangeSummary"):
            b["disclosureChangeSummary"] = _safe(
                lambda: disclosureChangeSummaryBlock(calcDisclosureChangeSummary(company, basePeriod=basePeriod))
            )
        if _need("keyTopicChanges"):
            b["keyTopicChanges"] = _safe(
                lambda: keyTopicChangesBlock(calcKeyTopicChanges(company, basePeriod=basePeriod))
            )
        if _need("changeIntensity"):
            b["changeIntensity"] = _safe(
                lambda: changeIntensityBlock(calcChangeIntensity(company, basePeriod=basePeriod))
            )
        if _need("disclosureDeltaFlags"):
            b["disclosureDeltaFlags"] = _safe(
                lambda: disclosureDeltaFlagsBlock(calcDisclosureDeltaFlags(company, basePeriod=basePeriod))
            )

    if keys is None or keys & {"peerRanking", "riskReturnPosition", "peerBenchmarkFlags"}:
        from dartlab.analysis.financial.peerBenchmark import (
            calcPeerBenchmarkFlags,
            calcPeerRanking,
            calcRiskReturnPosition,
        )
        from dartlab.story.builders import (
            peerBenchmarkFlagsBlock,
            peerRankingBlock,
            riskReturnPositionBlock,
        )

        if _need("peerRanking"):
            b["peerRanking"] = _safe(lambda: peerRankingBlock(calcPeerRanking(company, basePeriod=basePeriod)))
        if _need("riskReturnPosition"):
            b["riskReturnPosition"] = _safe(
                lambda: riskReturnPositionBlock(calcRiskReturnPosition(company, basePeriod=basePeriod))
            )
        if _need("peerBenchmarkFlags"):
            b["peerBenchmarkFlags"] = _safe(
                lambda: peerBenchmarkFlagsBlock(calcPeerBenchmarkFlags(company, basePeriod=basePeriod))
            )

    # ── 6부: 전망분석 ──
    if keys is None or keys & {
        "revenueForecast",
        "segmentForecast",
        "proFormaHighlights",
        "scenarioImpact",
        "forecastMethodology",
        "historicalRatios",
        "forecastFlags",
        "calibrationReport",
    }:
        from dartlab.analysis.financial.forecastCalcs import (
            calcCalibrationReport,
            calcForecastFlags,
            calcForecastMethodology,
            calcHistoricalRatios,
            calcProFormaHighlights,
            calcRevenueForecast,
            calcScenarioImpact,
            calcSegmentForecast,
        )
        from dartlab.story.builders import (
            calibrationReportBlock,
            forecastFlagsBlock,
            forecastMethodologyBlock,
            historicalRatiosBlock,
            proFormaHighlightsBlock,
            revenueForecastBlock,
            scenarioImpactBlock,
            segmentForecastBlock,
        )

        if _need("revenueForecast"):
            b["revenueForecast"] = _safe(
                lambda: revenueForecastBlock(calcRevenueForecast(company, basePeriod=basePeriod))
            )
        if _need("segmentForecast"):
            b["segmentForecast"] = _safe(
                lambda: segmentForecastBlock(calcSegmentForecast(company, basePeriod=basePeriod))
            )
        if _need("proFormaHighlights"):
            b["proFormaHighlights"] = _safe(
                lambda: proFormaHighlightsBlock(calcProFormaHighlights(company, basePeriod=basePeriod))
            )
        if _need("scenarioImpact"):
            b["scenarioImpact"] = _safe(lambda: scenarioImpactBlock(calcScenarioImpact(company, basePeriod=basePeriod)))
        if _need("forecastMethodology"):
            b["forecastMethodology"] = _safe(
                lambda: forecastMethodologyBlock(calcForecastMethodology(company, basePeriod=basePeriod))
            )
        if _need("historicalRatios"):
            b["historicalRatios"] = _safe(
                lambda: historicalRatiosBlock(calcHistoricalRatios(company, basePeriod=basePeriod))
            )
        if _need("forecastFlags"):
            b["forecastFlags"] = _safe(lambda: forecastFlagsBlock(calcForecastFlags(company, basePeriod=basePeriod)))
        if _need("calibrationReport"):
            b["calibrationReport"] = _safe(
                lambda: calibrationReportBlock(calcCalibrationReport(company, basePeriod=basePeriod))
            )

    # ── 비교분석 (scan 교차 조합 관점 → story 통합) ──
    if keys is None or keys & {"peerPosition", "governanceSummary"}:
        from dartlab.scan.extended import calcGovernanceSummary, calcPeerPosition
        from dartlab.story.builders import peerPositionBlock
        from dartlab.story.builders import quantModuleBlock as _scanBlock

        if _need("peerPosition"):
            b["peerPosition"] = _safe(lambda: peerPositionBlock(calcPeerPosition(company)))
        if _need("governanceSummary"):
            b["governanceSummary"] = _safe(lambda: _scanBlock("governanceSummary", calcGovernanceSummary(company)))

    # ── 시장분석 (quant 기술적 분석 → story 통합) ──
    if keys is None or keys & {
        "technicalVerdict",
        "technicalSignals",
        "strategySnapshot",
        "marketBeta",
        "fundamentalDivergence",
        "marketAnalysisFlags",
    }:
        from dartlab.quant.extended import (
            calcCrosscheckData,
            calcFundamentalDivergence,
            calcMarketAnalysisFlags,
            calcMarketBeta,
            calcQuantConclusionData,
            calcRiskData,
            calcSignalData,
            calcStrategyData,
            calcStrategySnapshot,
            calcTechnicalSignals,
            calcTechnicalVerdict,
            calcTrendData,
        )
        from dartlab.story.builders import (
            fundamentalDivergenceBlock,
            marketAnalysisFlagsBlock,
            marketBetaBlock,
            quantModuleBlock,
            strategySnapshotBlock,
            technicalSignalsBlock,
            technicalVerdictBlock,
        )
        from dartlab.story.narrate import (
            narrateCrosscheck,
            narrateQuantConclusion,
            narrateQuantRisk,
            narrateSignals,
            narrateStrategyVerdict,
            narrateTrend,
        )

        if _need("technicalVerdict"):
            b["technicalVerdict"] = _safe(lambda: technicalVerdictBlock(calcTechnicalVerdict(company)))
        if _need("technicalSignals"):
            b["technicalSignals"] = _safe(lambda: technicalSignalsBlock(calcTechnicalSignals(company)))
        # quant 서사 모듈 5+1 — review가 서사를 생성 (엔진=숫자만, story=이야기꾼)
        _narrate_map = {
            "trendNarrative": (calcTrendData, lambda d: narrateTrend(d.get("verdict", {})) if d else ""),
            "riskNarrative": (calcRiskData, lambda d: narrateQuantRisk(d.get("data"), d.get("verdict")) if d else ""),
            "signalNarrative": (calcSignalData, lambda d: narrateSignals(d.get("data")) if d else ""),
            "strategyNarrative": (calcStrategyData, lambda d: narrateStrategyVerdict(d.get("data")) if d else ""),
            "crosscheckNarrative": (calcCrosscheckData, lambda d: narrateCrosscheck(d.get("data")) if d else ""),
            "quantConclusion": (
                calcQuantConclusionData,
                lambda d: narrateQuantConclusion(
                    d.get("trend_label", ""),
                    d.get("bullish", 0),
                    d.get("bearish", 0),
                    d.get("active_styles", []),
                    d.get("diagnosis", ""),
                )
                if d
                else "",
            ),
        }
        for qkey, (qcalc, qnarrate) in _narrate_map.items():
            if _need(qkey):

                def _build(c=qcalc, n=qnarrate):
                    data = c(company)
                    narrative = n(data) if data else ""
                    return quantModuleBlock(qkey, {"narrative": narrative, "data": data})

                b[qkey] = _safe(_build)
        if _need("strategySnapshot"):
            b["strategySnapshot"] = _safe(lambda: strategySnapshotBlock(calcStrategySnapshot(company)))
        if _need("marketBeta"):
            b["marketBeta"] = _safe(lambda: marketBetaBlock(calcMarketBeta(company)))
        if _need("fundamentalDivergence"):
            b["fundamentalDivergence"] = _safe(
                lambda: fundamentalDivergenceBlock(calcFundamentalDivergence(company, basePeriod=basePeriod))
            )
        if _need("marketAnalysisFlags"):
            b["marketAnalysisFlags"] = _safe(lambda: marketAnalysisFlagsBlock(calcMarketAnalysisFlags(company)))
        # Sprint 2~7 신규 12 alpha — 기존 quant 5+1 와 동일 _narrate_map 패턴 (story = 이야기꾼).
        # calc → narrate → quantModuleBlock(key, {narrative, data}) 통일 흐름.
        _alpha_market = "US" if getattr(company, "currency", "KRW") == "USD" else "KR"
        _stockCode = getattr(company, "stockCode", None)

        from dartlab.quant.alphas.accruals import calcAccrualsFactor
        from dartlab.quant.alphas.altman import calcAltmanFactor
        from dartlab.quant.alphas.bab import calcBAB
        from dartlab.quant.alphas.beneish import calcBeneishFactor
        from dartlab.quant.alphas.earningsSurprise import calcEarningsSurprise
        from dartlab.quant.alphas.fundamentalMomentum import calcFundamentalMomentum
        from dartlab.quant.alphas.piotroski import calcPiotroskiFactor
        from dartlab.quant.alphas.qFactor import calcQFactor
        from dartlab.quant.alphas.qmj import calcQMJ
        from dartlab.quant.factor import calcFactorICAll, calcFactorTearSheetAll, calcMultiFactorRisk
        from dartlab.story.narrate import (
            narrateAccruals,
            narrateAltman,
            narrateBAB,
            narrateBeneish,
            narrateEarningsSurprise,
            narrateFactorIC,
            narrateFactorTearSheet,
            narrateFundMomentum,
            narratePiotroski,
            narrateQFactor,
            narrateQMJ,
            narrateRiskDecomposition,
        )

        _alpha_map: dict[str, tuple] = {
            # alpha key : (calc 호출 callable, narrate 함수)
            "altmanFactor": (lambda: calcAltmanFactor(market=_alpha_market), narrateAltman),
            "piotroskiFactor": (lambda: calcPiotroskiFactor(market=_alpha_market), narratePiotroski),
            "beneishFactor": (lambda: calcBeneishFactor(market=_alpha_market), narrateBeneish),
            "accrualsFactor": (lambda: calcAccrualsFactor(market=_alpha_market), narrateAccruals),
            "qFactor": (lambda: calcQFactor(market=_alpha_market), narrateQFactor),
            "qmj": (lambda: calcQMJ(market=_alpha_market), narrateQMJ),
            "bab": (lambda: calcBAB(market=_alpha_market), narrateBAB),
            "earningsSurprise": (lambda: calcEarningsSurprise(market=_alpha_market), narrateEarningsSurprise),
            "fundMomentum": (lambda: calcFundamentalMomentum(market=_alpha_market), narrateFundMomentum),
            "factorTearSheet": (lambda: calcFactorTearSheetAll(market=_alpha_market), narrateFactorTearSheet),
            "factorIC": (lambda: calcFactorICAll(market=_alpha_market, horizon=5), narrateFactorIC),
        }
        # riskDecomposition 만 stockCode 필수 (단일 종목)
        if _stockCode:
            _alpha_map["riskDecomposition"] = (
                lambda: calcMultiFactorRisk(_stockCode),
                narrateRiskDecomposition,
            )

        for akey, (acalc, anarrate) in _alpha_map.items():
            if _need(akey):

                def _build(c=acalc, n=anarrate, k=akey):
                    data = c()
                    narrative = n(data) if data else ""
                    return quantModuleBlock(k, {"narrative": narrative, "data": data})

                b[akey] = _safe(_build)

    # ── 매크로 (시장 환경 + 기업-매크로 연결) ──
    _MACRO_KEYS = {
        "macroEnvironment",
        "macroCycle",
        "macroRates",
        "macroLiquidity",
        "macroSentiment",
        "macroForecast",
        "macroCorporate",
        "macroTrade",
        "macroFlags",
        "valuationBand",
        "companyCyclePosition",
        "macroSensitivity",
    }
    if keys is None or keys & _MACRO_KEYS:
        from dartlab.analysis.financial.macroExposure import calcValuationBand
        from dartlab.story.builders import (
            macroCorporateBlock,
            macroCycleBlock,
            macroEnvironmentBlock,
            macroFlagsBlock,
            macroForecastBlock,
            macroLiquidityBlock,
            macroRatesBlock,
            macroSensitivityBlock,
            macroSentimentBlock,
            macroTradeBlock,
            valuationBandBlock,
        )

        # macro("종합") 1회 호출 + 캐시 — 11축 전부 포함
        _macro_summary: list = [None]
        _macro_market = getattr(company, "market", "KR")

        def _ensure_summary():
            if _macro_summary[0] is None:
                import dartlab as _dl

                try:
                    _macro_summary[0] = _dl.macro("종합", market=_macro_market)
                except (ValueError, TypeError, KeyError, OSError) as e:
                    import logging

                    logging.getLogger(__name__).debug("macro 종합 실패 (market=%s): %s", _macro_market, e)
                    _macro_summary[0] = {}
            return _macro_summary[0]

        if _need("macroEnvironment"):
            b["macroEnvironment"] = _safe(lambda: macroEnvironmentBlock(_ensure_summary()))
        if _need("macroCycle"):
            b["macroCycle"] = _safe(lambda: macroCycleBlock(_ensure_summary().get("cycle", {})))
        if _need("macroRates"):
            b["macroRates"] = _safe(lambda: macroRatesBlock(_ensure_summary().get("rates", {})))
        if _need("macroLiquidity"):
            b["macroLiquidity"] = _safe(lambda: macroLiquidityBlock(_ensure_summary().get("liquidity", {})))
        if _need("macroSentiment"):
            b["macroSentiment"] = _safe(lambda: macroSentimentBlock(_ensure_summary().get("sentiment", {})))
        if _need("macroForecast"):
            b["macroForecast"] = _safe(lambda: macroForecastBlock(_ensure_summary().get("forecast")))
        if _need("macroCorporate"):
            b["macroCorporate"] = _safe(lambda: macroCorporateBlock(_ensure_summary().get("corporate")))
        if _need("macroTrade"):
            _market = getattr(company, "market", "KR")
            if _market == "KR":
                b["macroTrade"] = _safe(lambda: macroTradeBlock(_ensure_summary().get("trade")))
        if _need("macroFlags"):
            b["macroFlags"] = _safe(lambda: macroFlagsBlock(_ensure_summary()))
        if _need("macroSensitivity"):
            from dartlab.analysis.financial.macroExposure import calcMacroSensitivity

            b["macroSensitivity"] = _safe(
                lambda: macroSensitivityBlock(calcMacroSensitivity(company, basePeriod=basePeriod))
            )
        if _need("valuationBand"):
            b["valuationBand"] = _safe(lambda: valuationBandBlock(calcValuationBand(company, basePeriod=basePeriod)))
        if _need("companyCyclePosition"):
            from dartlab.story.builders import companyCyclePositionBlock

            b["companyCyclePosition"] = _safe(lambda: companyCyclePositionBlock(_ensure_summary().get("crisis", {})))

    from dartlab.story.blockMap import BlockMap

    # ── 개선 시나리오 (How축) — improvementLevers는 안정성 그룹에서 미리 계산됨 ──
    if keys is None or keys & {"gradeUpgradePath", "technicalActionTargets", "cyclicalActionPlan"}:
        from dartlab.story.builders import (
            cyclicalActionPlanBlock,
            gradeUpgradePathBlock,
            technicalActionTargetsBlock,
        )

        if _need("gradeUpgradePath"):
            from dartlab.credit.calcs import calcGradeImprovement

            b["gradeUpgradePath"] = _safe(
                lambda: gradeUpgradePathBlock(calcGradeImprovement(company, basePeriod=basePeriod))
            )
        if _need("technicalActionTargets"):
            from dartlab.quant.extended import calcActionableTargets

            b["technicalActionTargets"] = _safe(lambda: technicalActionTargetsBlock(calcActionableTargets(company)))
        if _need("cyclicalActionPlan"):
            from dartlab.macro.crisis import calcCyclicalAction

            _market = getattr(company, "market", "KR")
            b["cyclicalActionPlan"] = _safe(lambda: cyclicalActionPlanBlock(calcCyclicalAction(market=_market)))

    # ── Damodaran 3-test (스토리 검증) ──
    if keys is None or keys & {"damodaran3test"}:
        from dartlab.story.builders import damodaran3testBlock

        if _need("damodaran3test"):
            b["damodaran3test"] = _safe(lambda: damodaran3testBlock(company))

    # ── 메모리 해제 힌트 ──
    import gc

    gc.collect()

    return BlockMap(b)


def buildStory(
    company,
    section: str | None = None,
    layout: StoryLayout | None = None,
    helper: bool | None = None,
    *,
    type: str | None = None,
    template: str | None = None,
    detail: bool | None = None,
    basePeriod: str | None = None,
    hypothesis: str | None = None,  # thesis 타입 전용
    # ── deprecated (한 릴리즈 경고 후 제거) ──
    preset: str | None = None,
    perspective: str | None = None,
):
    """Company에서 Review를 생성.

    Parameters
    ----------
    type : str, optional
        보고서 타입. full/executive/credit/valuation/growth/crisis/audit/
        dividend/governance/macro/thesis. 기본 full.
    template : str, optional
        기업유형 감지 (독립 축). "auto" 또는 사이클/프랜차이즈/턴어라운드/...
    preset, perspective : deprecated
        type= 로 이전. 임시로 매핑 지원.
    """
    import warnings

    from dartlab.story import Story
    from dartlab.story.reportTypes import resolveReportType

    ly = layout or StoryLayout()

    # ── deprecated 파라미터 매핑 ──
    if perspective is not None and type is None:
        warnings.warn(
            "story(perspective=...) 는 deprecated. story(type=...) 를 사용하세요.",
            DeprecationWarning,
            stacklevel=3,
        )
        type = perspective
    if preset is not None and type is None:
        warnings.warn(
            "story(preset=...) 는 deprecated. story(type=...) 를 사용하세요.",
            DeprecationWarning,
            stacklevel=3,
        )
        type = preset

    # ── ReportType 해석 ──
    reportType = resolveReportType(type)

    # ── thesis 타입: 서사 주도 특수 경로 (블록화 예외) ──
    if reportType.key == "thesis":
        from dartlab.story.builders import thesisReportBlocks

        corpName = getattr(company, "corpName", "")
        stockCode = getattr(company, "stockCode", "")
        story = Story(stockCode=stockCode, corpName=corpName, layout=ly)
        thesis_blocks = thesisReportBlocks(company, hypothesis)
        story.sections = [Section(key="thesisReport", partId="T", title="논제 검증", blocks=thesis_blocks)]
        return story

    # ── lifeCycle 기반 강조 블록 자동 설정 ──
    # lifeCycle phase 에 따라 어떤 분석 관점이 중요한지 자동 결정
    _LIFECYCLE_EMPHASIZE: dict[str, set[str]] = {
        "earlyGrowth": {"revenueGrowth", "segmentComposition", "cashFlowOverview", "lifeCycleStage"},
        "highGrowth": {"revenueGrowth", "marginTrend", "capitalAllocation", "lifeCycleStage"},
        "matureGrowth": {"returnTrend", "capitalAllocation", "cashQuality", "lifeCycleStage"},
        "matureStable": {"dividendPolicy", "cashFlowOverview", "capitalAllocation", "lifeCycleStage"},
        "decline": {"leverageTrend", "distressSignals", "cashFlowOverview", "lifeCycleStage"},
        "turnaround": {"marginTrend", "cashFlowOverview", "leverageTrend", "lifeCycleStage"},
    }
    try:
        from dartlab.analysis.financial.lifeCycle import calcLifeCycle as _calcLC

        _lcResult = _calcLC(company, basePeriod=basePeriod)
        _lcPhase = _lcResult.get("phase") if _lcResult else None
    except (ImportError, AttributeError, TypeError, ValueError):
        _lcPhase = None

    # ── 스토리 템플릿 판별 (기업유형, ReportType과 독립) ──
    detectedTemplate: str | None = None
    detectedTemplates: list[str] = []
    emphasizedKeys: set[str] = set(reportType.emphasize)
    # lifeCycle 기반 강조 합산
    if _lcPhase and _lcPhase in _LIFECYCLE_EMPHASIZE:
        emphasizedKeys |= _LIFECYCLE_EMPHASIZE[_lcPhase]
    if template is not None:
        from dartlab.story.templates import STORY_TEMPLATES
        from dartlab.story.templates import detectTemplate as _detect

        if template == "auto":
            detectedTemplate = _detect(company)
            from dartlab.story.templates import detectTemplates as _detectMulti

            try:
                detectedTemplates = _detectMulti(company)
            except (AttributeError, ValueError, TypeError):
                detectedTemplates = []
        elif template in STORY_TEMPLATES:
            detectedTemplate = template
            detectedTemplates = [template]
        else:
            detectedTemplates = []

        if detectedTemplate and detectedTemplate in STORY_TEMPLATES:
            for tmplName in detectedTemplates:
                if tmplName in STORY_TEMPLATES:
                    emphasizedKeys |= STORY_TEMPLATES[tmplName].get("emphasize", set())

    # ── ReportType의 섹션 순서 적용 ──
    # (section 단일 지정이 아니고, layout.sectionOrder가 명시되지 않은 경우만)
    if section is None and ly.sectionOrder is None and type is not None:
        ly.sectionOrder = list(reportType.sectionOrder)
    if detail is None:
        ly.detail = reportType.detail

    # detail 명시 오버라이드
    if detail is not None:
        ly.detail = detail

    showHelper = helper if helper is not None else ly.helper

    corpName = getattr(company, "corpName", "")
    stockCode = getattr(company, "stockCode", "")

    story = Story(stockCode=stockCode, corpName=corpName, layout=ly)
    story.template = detectedTemplate
    story.templates = detectedTemplates if detectedTemplates else ([detectedTemplate] if detectedTemplate else [])

    useSpinner = isTerminal()
    if useSpinner:
        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        console = Console(stderr=True)
        spinner = Spinner("dots", text="분석 준비 중...")
        ctx = Live(spinner, console=console, transient=True)
    else:
        from contextlib import nullcontext

        ctx = nullcontext()

    with ctx as live:
        if live is not None:
            from rich.spinner import Spinner

            live.update(Spinner("dots", text="블록 사전 생성 중..."))

        # 템플릿 순서 결정 (블록 빌드 전에 필요한 keys 산출)
        if section is not None:
            if section not in TEMPLATES:
                available = ", ".join(sorted(TEMPLATES.keys()))
                raise ValueError(
                    f"'{section}' 섹션을 찾을 수 없습니다.\n"
                    f"  사용 가능한 섹션: {available}\n"
                    f"  사용법: c.story('수익구조') 또는 c.story() 로 전체 보고서"
                )
            templateKeys = [section]
        elif ly.sectionOrder is not None:
            templateKeys = [k for k in ly.sectionOrder if k in TEMPLATES]
        else:
            templateKeys = list(TEMPLATE_ORDER)

        # 필요한 블록 keys만 산출 → 선택적 빌드
        if section is not None and templateKeys:
            neededKeys: set[str] | None = set()
            for tk in templateKeys:
                neededKeys.update(TEMPLATES[tk]["keys"])
        else:
            neededKeys = None  # 전체 빌드

        b = buildBlocks(company, keys=neededKeys, basePeriod=basePeriod)

        for tmplKey in templateKeys:
            tmpl = TEMPLATES[tmplKey]
            if live is not None:
                from rich.spinner import Spinner

                live.update(Spinner("dots", text=f"{tmplKey} 조립 중..."))

            sectionBlocks = []
            for blockKey in tmpl["keys"]:
                blockList = b.get(blockKey)
                if blockList:
                    if blockKey in emphasizedKeys:
                        for blk in blockList:
                            if hasattr(blk, "emphasized"):
                                blk.emphasized = True
                    sectionBlocks.extend(blockList)

            if sectionBlocks:
                story.sections.append(
                    Section(
                        key=tmplKey,
                        partId=tmpl.get("partId", ""),
                        title=tmpl["title"],
                        blocks=sectionBlocks,
                        helper=tmpl.get("helper", "") if showHelper else "",
                        aiGuide=tmpl.get("aiGuide", ""),
                    )
                )

        # ── 순환 서사 감지 + 주입 ──
        if live is not None:
            from rich.spinner import Spinner

            live.update(Spinner("dots", text="순환 서사 감지 중..."))

        from dartlab.story.narrative import buildCirculationSummary, detectThreads

        _sectionSet = set(templateKeys) if section is not None else None
        threads = detectThreads(company, b, sections=_sectionSet)
        for thread in threads:
            for sec in story.sections:
                if sec.key in thread.involvedSections:
                    sec.threads.append(thread)
        story.circulationSummary = buildCirculationSummary(threads) if threads else ""

        # ── 6막 전환 인과 문장 ──
        from dartlab.story.narrative import buildActTransitions

        story.actTransitions = buildActTransitions(company, b)

        # ── 요약 카드 생성 ──
        from dartlab.story.summary import buildSectionSummary, buildSummaryCard

        scorecardData = None
        try:
            from dartlab.analysis.financial.scorecard import calcScorecard

            scorecardData = calcScorecard(company, basePeriod=basePeriod)
        except (ImportError, KeyError, ValueError, TypeError, AttributeError):
            pass

        story.summaryCard = buildSummaryCard(threads, scorecardData, story.sections)

        # ── 섹션별 요약 생성 ──
        for sec in story.sections:
            sec.summary = buildSectionSummary(sec)

    # ── type=None(기본)일 때 보고서 상단에 타입 가이드 삽입 ──
    if type is None and section is None:
        from dartlab.story.blocks import TextBlock

        guide = (
            "보고서 타입 안내: "
            "c.story(type='executive') 경영 3분컷 / "
            "type='credit' 신용분석 / "
            "type='dividend' 배당 / "
            "type='governance' 지배구조 / "
            "type='macro' 매크로 / "
            "type='thesis' 가설 검증"
        )
        if story.sections:
            story.sections[0].blocks.insert(0, TextBlock(guide, style="dim"))

    return story


# [Phase 3 워밍업 함수는 제거됨 — 위 buildBlocks 주석 참조]
