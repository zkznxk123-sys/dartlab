"""analysis L2 분리 모듈 import smoke + 순수함수 단위 테스트.

L2 리팩터링으로 분리된 모듈의 BC re-export 보장 + 순수함수 동작 검증.

대상:
- analysis/valuation/dcf.py (multiStageDcf, twoStageDcf, dcfValuation, relativeValuation,
  sensitivityAnalysis, liquidationValuation, fullValuation)
- analysis/forecast/simulation.py (simulateScenario, simulateAllScenarios,
  monteCarloForecast, stressTest)
- analysis/forecast/revenueForecast.py (forecastRevenue, applyAiOverlay,
  분리된 헬퍼들)
- analysis/financial/{capital, governance, earningsQuality, proforma, valuation,
  profitability} 분리 후 BC 호환
"""

import numpy as np

# ══════════════════════════════════════
# analysis/valuation/dcf.py 순수함수
# ══════════════════════════════════════


class TestMultiStageDcf:
    def test_basicMultiPhase(self):
        from dartlab.analysis.valuation.dcf import multiStageDcf

        r = multiStageDcf(
            baseFcf=1e10,
            growthYears=[5, 3, 2],
            growthRates=[15.0, 8.0, 3.0],
            terminalGrowthRate=2.0,
            wacc=10.0,
            netDebt=2e10,
            shares=int(1e8),
        )
        assert isinstance(r, dict)
        assert "enterpriseValue" in r
        assert "warnings" in r

    def test_scalarInputs(self):
        from dartlab.analysis.valuation.dcf import multiStageDcf

        r = multiStageDcf(
            baseFcf=1e9,
            growthYears=5,
            growthRates=8.0,
            terminalGrowthRate=2.5,
            wacc=10.0,
            shares=int(1e7),
        )
        assert isinstance(r, dict)
        assert r["enterpriseValue"] > 0


class TestLiquidationValuation:
    def test_basic(self):
        from dartlab.analysis.valuation.dcf import liquidationValuation

        r = liquidationValuation(
            cash=100,
            receivables=50,
            inventory=30,
            tangibleAssets=200,
            intangibleAssets=20,
            otherAssets=10,
            totalLiabilities=150,
            shares=100,
        )
        assert "grossRecovery" in r
        assert "netToEquity" in r
        assert "weightedRecoveryRate" in r
        assert 0 < r["weightedRecoveryRate"] < 1

    def test_cashHeavyHighRecovery(self):
        from dartlab.analysis.valuation.dcf import liquidationValuation

        # 100% 현금 → 회수율 100%
        r = liquidationValuation(cash=1000, totalLiabilities=0)
        assert r["weightedRecoveryRate"] >= 0.99


# ══════════════════════════════════════
# analysis/forecast/simulation.py BC re-export
# ══════════════════════════════════════


def test_simulationBcReexport():
    """simulation 분리 후 BC re-export 검증."""
    from dartlab.analysis.forecast.simulation import (
        monteCarloForecast,
        simulateAllScenarios,
        simulateScenario,
        stressTest,
    )

    assert callable(simulateScenario)
    assert callable(simulateAllScenarios)
    assert callable(monteCarloForecast)
    assert callable(stressTest)


# ══════════════════════════════════════
# analysis/forecast/revenueForecast.py BC re-export
# ══════════════════════════════════════


def test_revenueForecastBcReexport():
    """revenueForecast 분리 후 BC re-export 검증."""
    from dartlab.analysis.forecast.revenueForecast import (
        _classifyLifecycle,
        _computeWeights,
        _fetchConsensusRevenue,
        _fundamentalGrowth,
        _lifecycleWeightAdjustments,
        applyAiOverlay,
        forecastRevenue,
    )

    assert callable(forecastRevenue)
    assert callable(applyAiOverlay)
    assert callable(_fundamentalGrowth)
    assert callable(_classifyLifecycle)


# ══════════════════════════════════════
# analysis/financial 분리 모듈 BC re-export
# ══════════════════════════════════════


def test_capitalBcReexport():
    """capital.py 분리 후 BC re-export 검증."""
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

    assert callable(calcFundingSources)
    assert callable(calcCapitalFlags)


def test_governanceBcReexport():
    """governance.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.financial.governance import (
        calcAuditOpinionTrend,
        calcBoardComposition,
        calcCEOTurnover,
        calcExecutivePayDivergence,
        calcGovernanceFlags,
        calcIndependentDirectorQuality,
        calcLegalEventRisk,
        calcOwnerConcentration,
        calcOwnershipTrend,
        calcRelatedPartyIntensity,
    )

    assert callable(calcGovernanceFlags)
    assert callable(calcOwnerConcentration)


def test_earningsQualityBcReexport():
    """earningsQuality.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.financial.earningsQuality import (
        calcAccrualAnalysis,
        calcBeneishMScore,
        calcBeneishTimeline,
        calcDilutionTrend,
        calcEarningsPersistence,
        calcEarningsQualityFlags,
        calcNonOperatingBreakdown,
        calcQualityAnomalies,
        calcRichardsonAccrual,
        calcSloanAccruals,
    )

    assert callable(calcBeneishTimeline)
    assert callable(calcQualityAnomalies)


def test_proformaBcReexport():
    """proforma.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.financial.proforma import (
        HistoricalRatios,
        _fetchBeta,
        buildProforma,
        computeCompanyWacc,
        extractHistoricalRatios,
    )

    assert callable(buildProforma)
    assert callable(computeCompanyWacc)
    assert HistoricalRatios is not None


def test_valuationBcReexport():
    """valuation.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.financial.valuation import (
        _classifyCompanyType,
        calcDcf,
        calcDdm,
        calcNavValuation,
        calcPriceTarget,
        calcRelativeValuation,
        calcResidualIncome,
        calcReverseImplied,
        calcSensitivity,
        calcValuationFlags,
        calcValuationSynthesis,
    )

    assert callable(calcPriceTarget)
    assert callable(calcValuationSynthesis)


def test_profitabilityBcReexport():
    """profitability.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.financial.profitability import (
        calcMarginTrend,
        calcMarginWaterfall,
        calcPenmanDecomposition,
        calcProfitabilityFlags,
        calcReturnTrend,
        calcRoicTree,
    )

    assert callable(calcMarginWaterfall)
    assert callable(calcPenmanDecomposition)
    assert callable(calcRoicTree)


def test_predictionSignalsBcReexport():
    """predictionSignals 6 분리 모듈 후 BC re-export."""
    from dartlab.analysis.financial.predictionSignals import (
        calcConsensusDirection,
        calcDisclosureDelta,
        calcEarningsMomentum,
        calcEventImpact,
        calcFlowDirection,
        calcInventoryDivergence,
        calcMacroRegression,
        calcMacroSensitivity,
        calcPeerPrediction,
        calcRevenueDirection,
        calcStructuralBreak,
    )

    assert callable(calcConsensusDirection)
    assert callable(calcPeerPrediction)


def test_gradingBcReexport():
    """grading 분리 4 도메인 후 BC re-export."""
    from dartlab.analysis.financial.insight.grading import (
        analyzeCashflow,
        analyzeHealth,
        analyzeOpportunitySummary,
        analyzePerformance,
        analyzeProfitability,
        analyzeRiskSummary,
    )

    assert callable(analyzePerformance)
    assert callable(analyzeHealth)


def test_dcfBcReexport():
    """dcf.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.valuation.dcf import (
        dcfValuation,
        fullValuation,
        liquidationValuation,
        multiStageDcf,
        relativeValuation,
        sensitivityAnalysis,
        twoStageDcf,
    )

    assert callable(multiStageDcf)
    assert callable(relativeValuation)
    assert callable(sensitivityAnalysis)
    assert callable(liquidationValuation)


def test_dFVBcReexport():
    """dFV.py 분리 후 BC re-export 검증."""
    from dartlab.analysis.valuation.dFV import calcDFV

    assert callable(calcDFV)


# ══════════════════════════════════════
# Top-level Analysis facade
# ══════════════════════════════════════


def test_analysisFacade():
    """analysis.financial.Analysis facade 정상 작동."""
    from dartlab.analysis.financial import Analysis

    assert Analysis is not None
