"""Analyst 엔진 — 멀티소스 종합 분석.

Usage::

    from dartlab.analysis.valuation.analyst import Analyst

    a = Analyst()
    report = a.report(company, current_price=200000)
    log.info(report)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dartlab.core.types import MarketSnapshot

# Gather 는 runtime 에 core.di.getMacroProvider 경유 (정공법 B+C — gather 직접 의존 X)
# type 주석은 문자열로 ("Gather") — TYPE_CHECKING import 도 lint-imports 위반이라 제거
from .synthesizer import synthesize
from .types import AnalystReport, ValuationMethod

if TYPE_CHECKING:
    from dartlab.analysis.forecast.forecast import (
        ForecastResult,
        ScenarioResult,
        SensitivityResult,
    )
    from dartlab.analysis.forecast.revenueForecast import RevenueForecastResult
    from dartlab.analysis.forecast.simulation import (
        MonteCarloResult,
        SimulationResult,
        StressTestResult,
    )
    from dartlab.analysis.valuation.dcf import (
        DCFResult,
        DDMResult,
        RelativeValuationResult,
        ValuationSummary,
    )

log = logging.getLogger(__name__)


class Analyst:
    """종합 애널리스트 엔진 facade.

    DCF + 시장 데이터 → 가중평균 목표가 + 투자의견.

    Example::

        a = Analyst()
        report = a.report(company, current_price=200000)
        log.info(report.target_price)
        log.info(report.opinion)
    """

    def __init__(self, gather: Any = None) -> None:
        if gather is None:
            from dartlab.core.di import getMacroProvider

            self._gather = getMacroProvider().getDefaultGather()
        else:
            self._gather = gather
        self._owns_gather = gather is None

    def report(
        self,
        company=None,
        *,
        stockCode: str = "",
        companyName: str = "",
        currentPrice: float = 0.0,
        dcfTarget: float | None = None,
        dcfConfidence: float = 0.5,
        shares: int = 0,
        companyFinancials: dict | None = None,
        marketSnapshot: MarketSnapshot | None = None,
    ) -> AnalystReport:
        """종합 애널리스트 리포트 생성.

        Args:
            company: dartlab Company 객체 (있으면 자동 추출).
            stock_code: 종목코드.
            company_name: 회사명.
            current_price: 현재 주가 (0이면 시장에서 수집).
            dcf_target: DCF 목표가 (없으면 DCF skip).
            dcf_confidence: DCF 신뢰도.
            shares: 발행주식수.
            company_financials: EPS/BPS/EBITDA dict.
            market_snapshot: 미리 수집한 MarketSnapshot.

        Returns:
            AnalystReport.
        """
        # Company 객체에서 자동 추출
        if company is not None:
            stockCode, companyName, shares, companyFinancials = _extractFromCompany(
                company, stockCode, companyName, shares, companyFinancials
            )

        # 시장 데이터 수집
        if marketSnapshot is None and stockCode:
            try:
                snap = self._gather.collect(stockCode)
                marketSnapshot = snap.toMarketSnapshot()
            except OSError as exc:
                log.warning("시장 데이터 수집 실패: %s", exc)

        # 현재가 — 시장에서 가져오기
        if currentPrice <= 0 and marketSnapshot and marketSnapshot.currentPrice > 0:
            currentPrice = marketSnapshot.currentPrice

        # 합성
        return synthesize(
            dcfTarget=dcfTarget,
            dcfConfidence=dcfConfidence,
            market=marketSnapshot,
            companyFinancials=companyFinancials,
            shares=shares,
            currentPrice=currentPrice,
            companyName=companyName,
            stockCode=stockCode,
        )

    def collectMarket(self, stockCode: str) -> MarketSnapshot:
        """시장 데이터만 수집.

        Parameters
        ----------
        stock_code : str
            종목코드.

        Returns
        -------
        MarketSnapshot
            현재가, 시가총액, 거래량 등 시장 스냅샷.
        """
        return self._gather.collect(stockCode).toMarketSnapshot()

    def close(self) -> None:
        """리소스 정리.

        Returns
        -------
        None
        """
        if self._owns_gather:
            self._gather.close()

    def __repr__(self) -> str:
        return "Analyst()"


def _extractFromCompany(
    company,
    stockCode: str,
    companyName: str,
    shares: int,
    financials: dict | None,
) -> tuple[str, str, int, dict | None]:
    """Company 객체에서 필요한 정보 추출."""
    # 종목코드
    if not stockCode:
        try:
            stockCode = getattr(company, "stockCode", "") or getattr(company, "stock_code", "")
        except AttributeError:
            pass

    # 회사명
    if not companyName:
        try:
            companyName = getattr(company, "name", "") or ""
        except AttributeError:
            pass

    # 발행주식수
    if shares <= 0:
        try:
            profile = getattr(company, "profile", None)
            if profile:
                shares_val = getattr(profile, "sharesOutstanding", 0)
                if shares_val:
                    shares = int(shares_val)
        except (AttributeError, TypeError, ValueError):
            pass

    # 재무 데이터 — EPS, BPS
    if financials is None:
        financials = {}
        try:
            ratios = company._finance.ratios
            if ratios is not None:
                eps = ratios.get("eps") if isinstance(ratios, dict) else getattr(ratios, "eps", None)
                bps = ratios.get("bps") if isinstance(ratios, dict) else getattr(ratios, "bps", None)
                if eps:
                    financials["eps"] = float(eps)
                if bps:
                    financials["bps"] = float(bps)
        except (AttributeError, TypeError, ValueError):
            pass

    return stockCode, companyName, shares, financials or None


__all__ = [
    "Analyst",
    "AnalystReport",
    "ValuationMethod",
    # forecast
    "ForecastResult",
    "ScenarioResult",
    "SensitivityResult",
    # valuation
    "DCFResult",
    "DDMResult",
    "RelativeValuationResult",
    "ValuationSummary",
    # simulation
    "SimulationResult",
    "MonteCarloResult",
    "StressTestResult",
    # revenue forecast
    "RevenueForecastResult",
]


# ── lazy re-export (순환 의존 방지) ──

_LAZY_MAP: dict[str, tuple[str, str]] = {
    "ForecastResult": ("dartlab.analysis.forecast.forecast", "ForecastResult"),
    "ScenarioResult": ("dartlab.analysis.forecast.forecast", "ScenarioResult"),
    "SensitivityResult": ("dartlab.analysis.forecast.forecast", "SensitivityResult"),
    "forecastMetric": ("dartlab.analysis.forecast.forecast", "forecastMetric"),
    "forecastAll": ("dartlab.analysis.forecast.forecast", "forecastAll"),
    "scenarioAnalysis": ("dartlab.analysis.forecast.forecast", "scenarioAnalysis"),
    "sensitivityAnalysis": ("dartlab.analysis.forecast.forecast", "sensitivityAnalysis"),
    "RevenueForecastResult": ("dartlab.analysis.forecast.revenueForecast", "RevenueForecastResult"),
    "forecastRevenue": ("dartlab.analysis.forecast.revenueForecast", "forecastRevenue"),
    "SimulationResult": ("dartlab.analysis.forecast.simulation", "SimulationResult"),
    "MonteCarloResult": ("dartlab.analysis.forecast.simulation", "MonteCarloResult"),
    "StressTestResult": ("dartlab.analysis.forecast.simulation", "StressTestResult"),
    "simulateScenario": ("dartlab.analysis.forecast.simulation", "simulateScenario"),
    "simulateAllScenarios": ("dartlab.analysis.forecast.simulation", "simulateAllScenarios"),
    "monteCarloForecast": ("dartlab.analysis.forecast.simulation", "monteCarloForecast"),
    "stressTest": ("dartlab.analysis.forecast.simulation", "stressTest"),
    "DCFResult": ("dartlab.analysis.valuation.dcf", "DCFResult"),
    "DDMResult": ("dartlab.analysis.valuation.dcf", "DDMResult"),
    "RelativeValuationResult": ("dartlab.analysis.valuation.dcf", "RelativeValuationResult"),
    "ValuationSummary": ("dartlab.analysis.valuation.dcf", "ValuationSummary"),
    "dcfValuation": ("dartlab.analysis.valuation.dcf", "dcfValuation"),
    "ddmValuation": ("dartlab.analysis.valuation.dcf", "ddmValuation"),
    "fullValuation": ("dartlab.analysis.valuation.dcf", "fullValuation"),
    "relativeValuation": ("dartlab.analysis.valuation.dcf", "relativeValuation"),
}


def __getattr__(name: str):
    if name in _LAZY_MAP:
        import importlib

        modPath, attr = _LAZY_MAP[name]
        mod = importlib.import_module(modPath)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
