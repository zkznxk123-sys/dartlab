"""Damodaran L1.5 valuation helpers.

The functions in this module are pure post-processing helpers. They do not
import L2 engines or L1.5 siblings. Recipe code supplies Company tables,
market data, and reference dictionaries explicitly.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

import polars as pl

_REVENUE = ("sales", "revenue", "revenues")
_EBIT = ("operating_profit", "operating_income", "operating_income_loss", "income_loss_from_operations")
_PRETAX = ("profit_before_tax", "income_before_tax", "pretax_income")
_TAX = ("income_taxes", "income_tax_expense", "taxes_expenses")
_CFO = (
    "operating_cashflow",
    "operating_cash_flow",
    "cash_flows_from_operating",
    "cash_flows_from_operating_activities",
    "net_cash_flows_from_operating_activities",
)
_CAPEX = (
    "purchase_of_property_plant_and_equipment",
    "payments_to_acquire_property_plant_and_equipment",
    "capital_expenditures",
)
_DEPRECIATION = (
    "depreciation_cf",
    "depreciation",
    "depreciation_amortization",
    "depreciation_depletion_and_amortization",
    "depreciation_other_amortization_and_impairment_losses_expense",
    "depreciationcash_flow",
)
_CASH = ("cash_and_cash_equivalents", "cash_and_equivalents", "cash_and_deposits")
_EQUITY = (
    "total_stockholders_equity",
    "stockholders_equity",
    "total_equity",
    "owners_of_parent_equity",
    "equity_including_nci",
    "equity_attributable_to_owners_of_parent",
)
_SHORT_DEBT = ("short_term_debt", "shortterm_borrowings", "short_term_borrowings")
_LONG_DEBT = ("long_term_debt", "longterm_borrowings", "long_term_borrowings", "borrowings")
_TOTAL_DEBT = ("debt_carrying_amount",)
_CURRENT_ASSETS = ("current_assets",)
_CURRENT_LIABILITIES = ("current_liabilities",)
_RECEIVABLES = (
    "trade_and_other_receivables",
    "trade_and_other_current_receivables",
    "trade_receivables",
    "accounts_receivable",
)
_INVENTORY = ("inventories", "inventory")
_PAYABLES = ("trade_and_other_payables", "trade_payables", "accounts_payable")


def buildDamodaranMemo(
    *,
    target: str,
    market: str,
    currency: str,
    companyName: str,
    statements: dict[str, pl.DataFrame],
    countryDefaults: dict[str, Any],
    industryDefaults: dict[str, Any],
    marketData: dict[str, Any] | None = None,
    industryKey: str | None = None,
    maxYears: int = 10,
) -> dict[str, Any]:
    """Build a Damodaran-style L1.5 valuation memo from raw tables.

    Parameters are explicit so recipes can orchestrate L1/L1.5 resources
    without this helper importing engines or sibling L1.5 modules.
    """

    market_data = marketData or {}
    resolved_industry_key = _resolveIndustryKey(target, companyName, industryKey, industryDefaults)
    country_code = _resolveCountryCode(market, currency, countryDefaults)
    country = (countryDefaults.get("countries") or {}).get(country_code) or {}
    industry = (industryDefaults.get("industries") or {}).get(resolved_industry_key) or {}

    model_fit = _modelFit(target, companyName, resolved_industry_key, industry)
    panel, trace, panel_gaps = _buildPanel(statements, country, maxYears=maxYears)
    assumptions = _assumptions(countryDefaults, industryDefaults, country, industry, panel, resolved_industry_key)
    dcf = _dcfBand(panel, assumptions, market_data, model_fit)
    reverse = _reverseDcf(panel, assumptions, market_data, dcf, model_fit)
    relative = _relativeCheck(panel, market_data, market)
    gaps = _gapLedger(
        countryDefaults=countryDefaults,
        industryDefaults=industryDefaults,
        industryKey=resolved_industry_key,
        panel=panel,
        modelFit=model_fit,
        marketData=market_data,
        panelGaps=panel_gaps,
        reverse=reverse,
    )
    decision_status = _decisionStatus(model_fit, panel, market_data, gaps)

    latest_year = panel[0]["year"] if panel else None
    headline = {
        "decisionScore": _decisionScore(decision_status),
        "target": target,
        "market": market,
        "decisionStatus": decision_status,
        "baseEquityValue": _round(dcf.get("base", {}).get("equityValue")),
        "marketCap": _round(market_data.get("marketCap")),
        "upsidePct": _round(dcf.get("base", {}).get("upsidePct"), 2),
        "reverseRequiredGrowthPct": _round(reverse.get("requiredGrowthPct"), 2),
        "storyboardReady": decision_status in {"usable", "usableWithFallback"} and reverse.get("status") != "blocked",
    }

    sources = _sources(countryDefaults, industryDefaults)
    tables = {
        "dataAudit": _dataAuditTable(statements, countryDefaults, industryDefaults, market_data, panel, gaps),
        "modelFit": [model_fit],
        "lifeCycleClassifier": _lifeCycleTable(panel, assumptions, model_fit),
        "normalizedFinancials": panel[:maxYears],
        "accountTraceAudit": _accountTraceTable(trace, panel),
        "reinvestmentRoc": _valueDriverTable(panel, assumptions),
        "growthFeasibility": _growthFeasibilityTable(panel, assumptions, reverse, model_fit),
        "costOfCapital": _costOfCapitalTable(assumptions),
        "fcffDcf": _dcfTable(dcf),
        "relativeCheck": [relative],
        "scenarioFalsifier": _scenarioTable(dcf, reverse),
        "deepDive": _deepDiveTable(decision_status, model_fit, dcf, reverse, gaps),
    }

    return {
        "target": target,
        "market": market,
        "currency": currency,
        "companyName": companyName,
        "industryKey": resolved_industry_key,
        "countryCode": country_code,
        "asOf": market_data.get("priceDate") or latest_year or countryDefaults.get("_meta", {}).get("asOfDate"),
        "decisionStatus": decision_status,
        "headline": headline,
        "units": {
            "decisionScore": "score",
            "baseEquityValue": currency,
            "marketCap": currency,
            "upsidePct": "%",
            "reverseRequiredGrowthPct": "%",
        },
        "modelFit": model_fit,
        "normalizedPanel": panel,
        "trace": trace,
        "assumptions": assumptions,
        "dcfBand": dcf,
        "reverseDcf": reverse,
        "relativeCheck": relative,
        "gapLedger": gaps,
        "tables": tables,
        "sources": sources,
        "storyboardReady": headline["storyboardReady"],
    }


def _years(df: pl.DataFrame | None) -> list[str]:
    if not isinstance(df, pl.DataFrame):
        return []
    years = [str(col) for col in df.columns if str(col).isdigit() and len(str(col)) == 4]
    return sorted(years, reverse=True)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _value(df: pl.DataFrame | None, candidates: tuple[str, ...], year: str) -> tuple[float | None, str | None]:
    if not isinstance(df, pl.DataFrame) or "snakeId" not in df.columns or year not in df.columns:
        return None, None
    for candidate in candidates:
        rows = df.filter(pl.col("snakeId") == candidate)
        if rows.height == 0:
            continue
        val = _number(rows.get_column(year)[0])
        if val is not None:
            return val, candidate
    return None, None


def _sumValues(df: pl.DataFrame | None, candidates: tuple[str, ...], year: str) -> tuple[float | None, list[str]]:
    values: list[float] = []
    sources: list[str] = []
    if not isinstance(df, pl.DataFrame) or "snakeId" not in df.columns or year not in df.columns:
        return None, []
    for candidate in candidates:
        rows = df.filter(pl.col("snakeId") == candidate)
        if rows.height == 0:
            continue
        val = _number(rows.get_column(year)[0])
        if val is not None:
            values.append(val)
            sources.append(candidate)
    if not values:
        return None, []
    return sum(values), sources


def _debt(bs: pl.DataFrame | None, year: str) -> tuple[float | None, list[str]]:
    total, total_sources = _sumValues(bs, _TOTAL_DEBT, year)
    if total is not None:
        return total, total_sources
    short, short_sources = _sumValues(bs, _SHORT_DEBT, year)
    long, long_sources = _sumValues(bs, _LONG_DEBT, year)
    values = [v for v in (short, long) if v is not None]
    if not values:
        return 0.0, []
    return sum(values), short_sources + long_sources


def _nwc(bs: pl.DataFrame | None, year: str) -> tuple[float | None, list[str], str]:
    receivables, rec_src = _sumValues(bs, _RECEIVABLES, year)
    inventory, inv_src = _sumValues(bs, _INVENTORY, year)
    payables, pay_src = _sumValues(bs, _PAYABLES, year)
    if receivables is not None and inventory is not None and payables is not None:
        return receivables + inventory - payables, rec_src + inv_src + pay_src, "operatingAccounts"
    current_assets, ca_src = _value(bs, _CURRENT_ASSETS, year)
    current_liabilities, cl_src = _value(bs, _CURRENT_LIABILITIES, year)
    cash, cash_src = _value(bs, _CASH, year)
    if current_assets is not None and current_liabilities is not None:
        cash_value = cash or 0.0
        sources = [source for source in (ca_src, cl_src, cash_src) if source]
        return current_assets - cash_value - current_liabilities, sources, "currentMinusCash"
    return None, [], "missing"


def _buildPanel(
    statements: dict[str, pl.DataFrame],
    country: dict[str, Any],
    *,
    maxYears: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, str]]]:
    is_df = statements.get("IS")
    bs_df = statements.get("BS")
    cf_df = statements.get("CF")
    years = sorted(set(_years(is_df)) & set(_years(bs_df)) & set(_years(cf_df)), reverse=True)[: maxYears + 1]
    tax_fallback = (_number(country.get("taxRate")) or 25.0) / 100.0

    rows_by_year: dict[str, dict[str, Any]] = {}
    trace: dict[str, Any] = {}
    gaps: list[dict[str, str]] = []
    for year in years:
        revenue, revenue_src = _value(is_df, _REVENUE, year)
        ebit, ebit_src = _value(is_df, _EBIT, year)
        pretax, pretax_src = _value(is_df, _PRETAX, year)
        tax_expense, tax_src = _value(is_df, _TAX, year)
        cfo, cfo_src = _value(cf_df, _CFO, year)
        capex_raw, capex_src = _value(cf_df, _CAPEX, year)
        depreciation, depreciation_src = _value(cf_df, _DEPRECIATION, year)
        if depreciation is None:
            depreciation, depreciation_src = _value(is_df, _DEPRECIATION, year)
        cash, cash_src = _value(bs_df, _CASH, year)
        equity, equity_src = _value(bs_df, _EQUITY, year)
        debt, debt_src = _debt(bs_df, year)
        nwc, nwc_src, nwc_method = _nwc(bs_df, year)

        capex = abs(capex_raw) if capex_raw is not None else None
        if pretax and pretax > 0 and tax_expense is not None:
            tax_rate = _clamp(abs(tax_expense) / pretax, 0.0, 0.45)
            tax_rate_source = "reported"
        else:
            tax_rate = tax_fallback
            tax_rate_source = "countryFallback"
        nopat = ebit * (1.0 - tax_rate) if ebit is not None else None
        invested_capital = equity + (debt or 0.0) - (cash or 0.0) if equity is not None else None
        roc = nopat / invested_capital if nopat is not None and invested_capital and invested_capital > 0 else None
        sales_to_capital = (
            revenue / invested_capital if revenue is not None and invested_capital and invested_capital > 0 else None
        )
        margin = ebit / revenue if ebit is not None and revenue and revenue > 0 else None

        rows_by_year[year] = {
            "year": year,
            "revenue": revenue,
            "ebit": ebit,
            "operatingMarginPct": _pct(margin),
            "taxRatePct": _pct(tax_rate),
            "taxRateSource": tax_rate_source,
            "nopat": nopat,
            "cfo": cfo,
            "capex": capex,
            "depreciation": depreciation,
            "nonCashWorkingCapital": nwc,
            "nwcMethod": nwc_method,
            "cash": cash,
            "debt": debt,
            "equity": equity,
            "investedCapital": invested_capital,
            "rocPct": _pct(roc),
            "salesToCapital": sales_to_capital,
        }
        trace[year] = {
            "revenue": revenue_src,
            "ebit": ebit_src,
            "pretax": pretax_src,
            "tax": tax_src,
            "cfo": cfo_src,
            "capex": capex_src,
            "depreciation": depreciation_src,
            "cash": cash_src,
            "debt": debt_src,
            "equity": equity_src,
            "nwc": nwc_src,
        }

    chronological = sorted(rows_by_year)
    for idx, year in enumerate(chronological):
        row = rows_by_year[year]
        prev = rows_by_year[chronological[idx - 1]] if idx > 0 else None
        if prev:
            row["revenueGrowthPct"] = _pct(_growth(row.get("revenue"), prev.get("revenue")))
            if row.get("nonCashWorkingCapital") is not None and prev.get("nonCashWorkingCapital") is not None:
                row["deltaNwc"] = row["nonCashWorkingCapital"] - prev["nonCashWorkingCapital"]
            else:
                row["deltaNwc"] = None
        else:
            row["revenueGrowthPct"] = None
            row["deltaNwc"] = None
        if row.get("nopat") is not None and row.get("capex") is not None:
            depreciation = row.get("depreciation") or 0.0
            delta_nwc = row.get("deltaNwc")
            if delta_nwc is not None:
                row["reinvestment"] = row["capex"] - depreciation + delta_nwc
                row["fcff"] = row["nopat"] + depreciation - row["capex"] - delta_nwc
                row["fcffMethod"] = "nopatMinusReinvestment"
            elif row.get("cfo") is not None:
                row["reinvestment"] = None
                row["fcff"] = row["cfo"] - row["capex"]
                row["fcffMethod"] = "cfoMinusCapexFallback"
            else:
                row["reinvestment"] = None
                row["fcff"] = None
                row["fcffMethod"] = "missing"
        else:
            row["reinvestment"] = None
            row["fcff"] = None
            row["fcffMethod"] = "missing"
        row["reinvestmentRatePct"] = _pct(
            row["reinvestment"] / row["nopat"]
            if row.get("reinvestment") is not None and row.get("nopat") not in (None, 0.0)
            else None
        )

    panel = [rows_by_year[year] for year in sorted(rows_by_year, reverse=True)]
    for required in ("revenue", "ebit", "cfo", "capex", "investedCapital"):
        if not any(row.get(required) is not None for row in panel):
            gaps.append({"id": f"missing_{required}", "status": "deferredWithBlocker", "reason": required})
    return [_roundRow(row) for row in panel[:maxYears]], trace, gaps


def _assumptions(
    countryDefaults: dict[str, Any],
    industryDefaults: dict[str, Any],
    country: dict[str, Any],
    industry: dict[str, Any],
    panel: list[dict[str, Any]],
    industryKey: str,
) -> dict[str, Any]:
    rf = (_number(country.get("riskFreeRate")) or 4.0) / 100.0
    erp = (
        _number(country.get("totalERP")) or _number(countryDefaults.get("_meta", {}).get("matureMarketERP")) or 5.0
    ) / 100.0
    tax = (_number(country.get("taxRate")) or _median([row.get("taxRatePct") for row in panel]) or 25.0) / 100.0
    beta = _number(industry.get("beta")) or _number(industry.get("unleveredBeta")) or 1.0
    cost_of_equity = (_number(industry.get("costOfEquityPct")) or ((rf + beta * erp) * 100.0)) / 100.0
    after_tax_debt = (_number(industry.get("afterTaxCostOfDebtPct")) or 4.5) / 100.0
    debt_to_capital = (_number(industry.get("debtToCapitalPct")) or 0.0) / 100.0
    computed_wacc = cost_of_equity * (1.0 - debt_to_capital) + after_tax_debt * debt_to_capital
    wacc = (_number(industry.get("costOfCapitalPct")) or (computed_wacc * 100.0)) / 100.0
    recent_growth = _median([row.get("revenueGrowthPct") for row in panel[:5]]) or 3.0
    recent_margin = _median(
        [row.get("operatingMarginPct") for row in panel[:5] if row.get("operatingMarginPct") is not None]
    )
    industry_margin = _number(industry.get("preTaxOperatingMarginPct"))
    margin_pct = recent_margin if recent_margin is not None else industry_margin
    sales_to_capital = (
        _median([row.get("salesToCapital") for row in panel[:5]])
        or _number(industry.get("salesToInvestedCapital"))
        or 1.25
    )
    roc_pct = _median([row.get("rocPct") for row in panel[:5] if row.get("rocPct") is not None])
    implied_industry_roc = ((industry_margin or 10.0) / 100.0) * (1.0 - tax) * sales_to_capital * 100.0
    normalized_roc_pct = roc_pct if roc_pct is not None else implied_industry_roc
    terminal_growth = min(max(rf * 0.6, 0.01), max(wacc - 0.02, 0.005), 0.04)
    stable_roc = max(wacc + 0.015, min(max((normalized_roc_pct or 10.0) / 100.0, wacc + 0.015), 0.25))

    return {
        "riskFreeRatePct": _pct(rf),
        "erpPct": _pct(erp),
        "taxRatePct": _pct(tax),
        "beta": beta,
        "costOfEquityPct": _pct(cost_of_equity),
        "afterTaxCostOfDebtPct": _pct(after_tax_debt),
        "debtToCapitalPct": _pct(debt_to_capital),
        "waccPct": _pct(wacc),
        "recentGrowthPct": _clamp(recent_growth, -15.0, 25.0),
        "normalizedMarginPct": _clamp(margin_pct or 10.0, -20.0, 50.0),
        "salesToCapital": max(0.2, min(sales_to_capital, 6.0)),
        "normalizedRocPct": _pct(stable_roc),
        "terminalGrowthPct": _pct(terminal_growth),
        "industryKey": industryKey,
        "countryReferenceStatus": countryDefaults.get("_meta", {}).get("freshnessStatus", "unknown"),
        "industryCoverageStatus": industryDefaults.get("_meta", {}).get("coverageStatus", "unknown"),
    }


def _dcfBand(
    panel: list[dict[str, Any]],
    assumptions: dict[str, Any],
    marketData: dict[str, Any],
    modelFit: dict[str, Any],
) -> dict[str, Any]:
    if not modelFit.get("genericFcffEligible"):
        return {"status": "blocked", "reason": modelFit.get("modelType")}
    latest = _latestUsable(panel)
    if latest is None:
        return {"status": "blocked", "reason": "missingFinancialPanel"}
    revenue = _number(latest.get("revenue"))
    if revenue is None or revenue <= 0:
        return {"status": "blocked", "reason": "missingRevenue"}

    base_growth = _clamp((assumptions["recentGrowthPct"] or 3.0) / 100.0, -0.05, 0.12)
    base_margin = _clamp((assumptions["normalizedMarginPct"] or 10.0) / 100.0, -0.05, 0.45)
    wacc = max((assumptions["waccPct"] or 9.0) / 100.0, 0.04)
    terminal_growth = min((assumptions["terminalGrowthPct"] or 2.0) / 100.0, wacc - 0.015)
    sales_to_capital = max(_number(assumptions.get("salesToCapital")) or 1.25, 0.2)
    stable_roc = max((assumptions["normalizedRocPct"] or 10.0) / 100.0, wacc + 0.01)
    tax = _clamp((assumptions["taxRatePct"] or 25.0) / 100.0, 0.0, 0.45)
    net_debt = (latest.get("debt") or 0.0) - (latest.get("cash") or 0.0)
    market_cap = _number(marketData.get("marketCap"))
    shares = _number(marketData.get("shares"))

    scenarios = {
        "bear": {"growth": base_growth - 0.04, "margin": base_margin - 0.03, "wacc": wacc + 0.01},
        "base": {"growth": base_growth, "margin": base_margin, "wacc": wacc},
        "bull": {"growth": base_growth + 0.04, "margin": base_margin + 0.03, "wacc": max(wacc - 0.01, 0.04)},
    }
    out: dict[str, Any] = {"status": "usable"}
    for name, params in scenarios.items():
        result = _projectDcf(
            revenue=revenue,
            firstGrowth=_clamp(params["growth"], -0.15, 0.25),
            margin=_clamp(params["margin"], -0.15, 0.50),
            tax=tax,
            wacc=max(params["wacc"], terminal_growth + 0.015),
            terminalGrowth=terminal_growth,
            salesToCapital=sales_to_capital,
            stableRoc=stable_roc,
            netDebt=net_debt,
            shares=shares,
            marketCap=market_cap,
        )
        out[name] = result
    return out


def _projectDcf(
    *,
    revenue: float,
    firstGrowth: float,
    margin: float,
    tax: float,
    wacc: float,
    terminalGrowth: float,
    salesToCapital: float,
    stableRoc: float,
    netDebt: float,
    shares: float | None,
    marketCap: float | None,
) -> dict[str, Any]:
    forecast: list[dict[str, Any]] = []
    prev_revenue = revenue
    firm_value = 0.0
    for year in range(1, 6):
        fade = year / 5.0
        growth = firstGrowth * (1.0 - fade) + terminalGrowth * fade
        next_revenue = prev_revenue * (1.0 + growth)
        delta_revenue = next_revenue - prev_revenue
        nopat = next_revenue * margin * (1.0 - tax)
        reinvestment = delta_revenue / salesToCapital
        fcff = nopat - reinvestment
        pv = fcff / ((1.0 + wacc) ** year)
        firm_value += pv
        forecast.append(
            {
                "year": year,
                "growthPct": _pct(growth),
                "revenue": _round(next_revenue),
                "nopat": _round(nopat),
                "reinvestment": _round(reinvestment),
                "fcff": _round(fcff),
                "pvFcff": _round(pv),
            }
        )
        prev_revenue = next_revenue
    terminal_nopat = prev_revenue * (1.0 + terminalGrowth) * margin * (1.0 - tax)
    terminal_reinvestment_rate = min(max(terminalGrowth / stableRoc, 0.0), 0.95)
    terminal_fcff = terminal_nopat * (1.0 - terminal_reinvestment_rate)
    terminal_value = terminal_fcff / max(wacc - terminalGrowth, 0.005)
    pv_terminal = terminal_value / ((1.0 + wacc) ** 5)
    firm_value += pv_terminal
    equity_value = firm_value - netDebt
    per_share = equity_value / shares if shares and shares > 0 else None
    upside = (equity_value / marketCap - 1.0) * 100.0 if marketCap and marketCap > 0 else None
    terminal_share = pv_terminal / firm_value * 100.0 if firm_value else None
    return {
        "growthPct": _pct(firstGrowth),
        "marginPct": _pct(margin),
        "waccPct": _pct(wacc),
        "terminalGrowthPct": _pct(terminalGrowth),
        "firmValue": _round(firm_value),
        "equityValue": _round(equity_value),
        "perShare": _round(per_share),
        "upsidePct": _round(upside, 2),
        "terminalValueSharePct": _round(terminal_share, 2),
        "forecast": forecast,
    }


def _reverseDcf(
    panel: list[dict[str, Any]],
    assumptions: dict[str, Any],
    marketData: dict[str, Any],
    dcf: dict[str, Any],
    modelFit: dict[str, Any],
) -> dict[str, Any]:
    if not modelFit.get("genericFcffEligible"):
        return {"status": "blocked", "reason": modelFit.get("modelType")}
    latest = _latestUsable(panel)
    market_cap = _number(marketData.get("marketCap"))
    if latest is None or not market_cap:
        return {"status": "blocked", "reason": "missingMarketCap"}
    revenue = _number(latest.get("revenue"))
    if revenue is None or revenue <= 0:
        return {"status": "blocked", "reason": "missingRevenue"}
    net_debt = (latest.get("debt") or 0.0) - (latest.get("cash") or 0.0)
    target_firm_value = market_cap + net_debt
    margin = _clamp((assumptions["normalizedMarginPct"] or 10.0) / 100.0, -0.05, 0.45)
    wacc = max((assumptions["waccPct"] or 9.0) / 100.0, 0.04)
    terminal_growth = min((assumptions["terminalGrowthPct"] or 2.0) / 100.0, wacc - 0.015)
    tax = _clamp((assumptions["taxRatePct"] or 25.0) / 100.0, 0.0, 0.45)
    sales_to_capital = max(_number(assumptions.get("salesToCapital")) or 1.25, 0.2)
    stable_roc = max((assumptions["normalizedRocPct"] or 10.0) / 100.0, wacc + 0.01)

    lo, hi = -0.25, 0.40
    for _ in range(48):
        mid = (lo + hi) / 2.0
        value = _projectDcf(
            revenue=revenue,
            firstGrowth=mid,
            margin=margin,
            tax=tax,
            wacc=wacc,
            terminalGrowth=terminal_growth,
            salesToCapital=sales_to_capital,
            stableRoc=stable_roc,
            netDebt=net_debt,
            shares=None,
            marketCap=None,
        )["firmValue"]
        if value < target_firm_value:
            lo = mid
        else:
            hi = mid
    required_growth = (lo + hi) / 2.0
    normalized_growth = (assumptions.get("recentGrowthPct") or 0.0) / 100.0
    plausibility = "stretched" if required_growth - normalized_growth > 0.05 else "plausible"
    if required_growth > 0.25:
        plausibility = "implausible"
    return {
        "status": "usable",
        "targetFirmValue": _round(target_firm_value),
        "requiredGrowthPct": _pct(required_growth),
        "normalizedGrowthPct": _pct(normalized_growth),
        "plausibility": plausibility,
    }


def _relativeCheck(panel: list[dict[str, Any]], marketData: dict[str, Any], market: str) -> dict[str, Any]:
    latest = _latestUsable(panel)
    market_cap = _number(marketData.get("marketCap"))
    if latest is None or not market_cap:
        return {"status": "blocked", "reason": "missingMarketCap"}
    revenue = latest.get("revenue")
    ebit = latest.get("ebit")
    equity = latest.get("equity")
    debt = latest.get("debt") or 0.0
    cash = latest.get("cash") or 0.0
    ev = market_cap + debt - cash
    return {
        "status": "partial" if market == "US" else "usableWithFallback",
        "evSales": _round(ev / revenue, 2) if revenue else None,
        "evEbit": _round(ev / ebit, 2) if ebit and ebit > 0 else None,
        "priceBook": _round(market_cap / equity, 2) if equity and equity > 0 else None,
        "note": "US peer valuation scan missing" if market == "US" else "KR market snapshot available separately",
    }


def _modelFit(target: str, companyName: str, industryKey: str, industry: dict[str, Any]) -> dict[str, Any]:
    text = f"{target} {companyName} {industryKey}".lower()
    financial_tokens = ("bank", "banks", "insurance", "financial", "금융", "은행", "보험", "증권")
    financial = industry.get("modelFit") == "financialFirmOnly" or (
        industryKey != "totalMarketWithoutFinancials" and any(token in text for token in financial_tokens)
    )
    if financial:
        return {
            "modelType": "financialFirmOnly",
            "genericFcffEligible": False,
            "blockers": ["generic FCFF DCF is not valid for banks/insurers/financial firms"],
            "fallbackModel": "financialFirmExcessReturn",
        }
    return {
        "modelType": "genericFcff",
        "genericFcffEligible": True,
        "blockers": [],
        "fallbackModel": None,
    }


def _resolveCountryCode(market: str, currency: str, countryDefaults: dict[str, Any]) -> str:
    mapping = countryDefaults.get("currencyToCountry") or {}
    if currency in mapping:
        return str(mapping[currency])
    return "US" if market == "US" else "KR"


def _resolveIndustryKey(
    target: str, companyName: str, industryKey: str | None, industryDefaults: dict[str, Any]
) -> str:
    industries = industryDefaults.get("industries") or {}
    aliases = industryDefaults.get("aliases") or {}
    if industryKey:
        key = aliases.get(str(industryKey).lower(), industryKey)
        if key in industries:
            return key
    text = f"{target} {companyName}".lower()
    if target in {"005930", "000660", "INTC"} or any(
        token in text for token in ("semiconductor", "하이닉스", "삼성전자")
    ):
        return "semiconductor" if "semiconductor" in industries else "totalMarketWithoutFinancials"
    if target == "138930" or any(token in text for token in ("bank", "금융", "은행")):
        return "banksRegional" if "banksRegional" in industries else "totalMarketWithoutFinancials"
    return "totalMarketWithoutFinancials"


def _gapLedger(
    *,
    countryDefaults: dict[str, Any],
    industryDefaults: dict[str, Any],
    industryKey: str,
    panel: list[dict[str, Any]],
    modelFit: dict[str, Any],
    marketData: dict[str, Any],
    panelGaps: list[dict[str, str]],
    reverse: dict[str, Any],
) -> list[dict[str, str]]:
    gaps = list(panelGaps)
    if countryDefaults.get("_meta", {}).get("freshnessStatus") == "stale":
        gaps.append(
            {"id": "countryReferenceStale", "status": "fallbackAccepted", "reason": "Damodaran country ERP stale"}
        )
    if industryDefaults.get("_meta", {}).get("coverageStatus") != "full":
        gaps.append({"id": "industryCoverageSeed", "status": "fallbackAccepted", "reason": industryKey})
    if not marketData.get("marketCap"):
        gaps.append({"id": "marketCapMissing", "status": "deferredWithBlocker", "reason": "reverse DCF unavailable"})
    if not modelFit.get("genericFcffEligible"):
        gaps.append(
            {"id": "genericFcffBlocked", "status": "deferredWithBlocker", "reason": modelFit.get("modelType", "")}
        )
    if len(panel) < 5:
        gaps.append({"id": "shortFinancialPanel", "status": "fallbackAccepted", "reason": f"{len(panel)} years"})
    if reverse.get("status") == "blocked":
        gaps.append({"id": "reverseDcfBlocked", "status": "deferredWithBlocker", "reason": reverse.get("reason", "")})
    return gaps


def _decisionStatus(
    modelFit: dict[str, Any],
    panel: list[dict[str, Any]],
    marketData: dict[str, Any],
    gaps: list[dict[str, str]],
) -> str:
    if not modelFit.get("genericFcffEligible"):
        return "blockedFinancialFirm"
    if len(panel) < 3:
        return "blockedInsufficientFinancials"
    if not marketData.get("marketCap"):
        return "usableNoMarketComparison"
    blockers = [gap for gap in gaps if gap.get("status") == "deferredWithBlocker"]
    return "usableWithFallback" if blockers or gaps else "usable"


def _decisionScore(decisionStatus: str) -> float:
    scores = {
        "usable": 0.45,
        "usableWithFallback": 0.40,
        "usableNoMarketComparison": 0.25,
        "blockedFinancialFirm": 0.0,
        "blockedInsufficientFinancials": 0.0,
    }
    return scores.get(decisionStatus, 0.10)


def _dataAuditTable(
    statements: dict[str, pl.DataFrame],
    countryDefaults: dict[str, Any],
    industryDefaults: dict[str, Any],
    marketData: dict[str, Any],
    panel: list[dict[str, Any]],
    gaps: list[dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic in ("IS", "BS", "CF"):
        table = statements.get(topic)
        has_rows = isinstance(table, pl.DataFrame) and table.height > 0
        rows.append(
            {"area": topic, "status": "usable" if has_rows else "missing", "rows": getattr(table, "height", None)}
        )
    rows.append(
        {"area": "countryReference", "status": countryDefaults.get("_meta", {}).get("freshnessStatus", "unknown")}
    )
    rows.append(
        {"area": "industryReference", "status": industryDefaults.get("_meta", {}).get("coverageStatus", "unknown")}
    )
    rows.append({"area": "marketCap", "status": "usable" if marketData.get("marketCap") else "missing"})
    rows.append(
        {"area": "normalizedPanel", "status": "usable" if len(panel) >= 5 else "usableWithFallback", "rows": len(panel)}
    )
    rows.extend({"area": gap["id"], "status": gap["status"], "reason": gap.get("reason")} for gap in gaps)
    return rows


def _lifeCycleTable(
    panel: list[dict[str, Any]], assumptions: dict[str, Any], modelFit: dict[str, Any]
) -> list[dict[str, Any]]:
    if not modelFit.get("genericFcffEligible"):
        return [
            {
                "metric": "lifeCyclePhase",
                "value": "financialFirmOnly",
                "status": "blocked",
                "reason": "generic FCFF life-cycle path is not valid for financial firms",
            }
        ]
    if len(panel) < 3:
        return [
            {
                "metric": "lifeCyclePhase",
                "value": "insufficientPanel",
                "status": "blocked",
                "reason": f"{len(panel)} years",
            }
        ]

    latest = _latestUsable(panel) or {}
    growth = _number(assumptions.get("recentGrowthPct")) or 0.0
    margin = _number(assumptions.get("normalizedMarginPct")) or 0.0
    roc = _number(assumptions.get("normalizedRocPct")) or 0.0
    wacc = _number(assumptions.get("waccPct")) or 0.0
    fcff_values = [_number(row.get("fcff")) for row in panel[:5]]
    fcff_clean = [value for value in fcff_values if value is not None]
    fcff_positive_ratio = sum(1 for value in fcff_clean if value > 0) / len(fcff_clean) if fcff_clean else None

    if growth < -2.0:
        phase = "decline"
    elif margin < 0 or (fcff_positive_ratio is not None and fcff_positive_ratio < 0.4):
        phase = "turnaround"
    elif growth >= 12.0:
        phase = "highGrowth"
    elif growth >= 5.0 and roc > wacc:
        phase = "matureGrowth"
    else:
        phase = "matureStable"

    confidence = "high" if len(panel) >= 5 and fcff_positive_ratio is not None else "medium"
    return [
        {"metric": "lifeCyclePhase", "value": phase, "status": "usable", "confidence": confidence},
        {"metric": "recentGrowthPct", "value": _round(growth, 2), "status": "evidence", "source": "medianRecent"},
        {"metric": "normalizedMarginPct", "value": _round(margin, 2), "status": "evidence", "source": "panelMedian"},
        {
            "metric": "rocWaccSpreadPct",
            "value": _round(roc - wacc, 2),
            "status": "evidence",
            "source": "panelMinusWacc",
        },
        {
            "metric": "fcffPositiveRatio",
            "value": _round(fcff_positive_ratio, 3),
            "status": "evidence",
            "source": f"{len(fcff_clean)} years",
        },
        {"metric": "latestYear", "value": latest.get("year"), "status": "evidence", "source": "normalizedPanel"},
    ]


def _accountTraceTable(trace: dict[str, Any], panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_year = str(panel[0].get("year")) if panel else None
    latest_trace = trace.get(latest_year, {}) if latest_year else {}
    account_labels = {
        "revenue": "sales/revenue",
        "ebit": "operating profit",
        "pretax": "pretax income",
        "tax": "income tax",
        "cfo": "operating cash flow",
        "capex": "capital expenditure",
        "depreciation": "depreciation",
        "cash": "cash",
        "debt": "debt",
        "equity": "equity",
        "nwc": "non-cash working capital",
    }
    rows: list[dict[str, Any]] = []
    for key, label in account_labels.items():
        source = latest_trace.get(key)
        if isinstance(source, list):
            source_text = ";".join(str(item) for item in source if item)
        else:
            source_text = str(source) if source else ""
        status = "usable" if source_text else "missing"
        if key == "debt" and not source_text:
            status = "fallbackAccepted"
            source_text = "zeroDebtOrNoDebtLine"
        rows.append(
            {
                "year": latest_year,
                "account": label,
                "traceKey": key,
                "status": status,
                "source": source_text,
            }
        )
    return rows


def _valueDriverTable(panel: list[dict[str, Any]], assumptions: dict[str, Any]) -> list[dict[str, Any]]:
    latest = _latestUsable(panel) or {}
    return [
        {
            "metric": "salesToCapital",
            "value": _round(assumptions.get("salesToCapital"), 3),
            "source": "panelOrIndustryFallback",
        },
        {
            "metric": "normalizedRocPct",
            "value": _round(assumptions.get("normalizedRocPct"), 2),
            "source": "panelOrIndustryFallback",
        },
        {"metric": "latestRocPct", "value": latest.get("rocPct"), "source": latest.get("year")},
        {
            "metric": "latestReinvestmentRatePct",
            "value": latest.get("reinvestmentRatePct"),
            "source": latest.get("year"),
        },
        {"metric": "recentGrowthPct", "value": _round(assumptions.get("recentGrowthPct"), 2), "source": "medianRecent"},
    ]


def _growthFeasibilityTable(
    panel: list[dict[str, Any]],
    assumptions: dict[str, Any],
    reverse: dict[str, Any],
    modelFit: dict[str, Any],
) -> list[dict[str, Any]]:
    if not modelFit.get("genericFcffEligible"):
        return [
            {
                "metric": "growthFeasibility",
                "value": "blocked",
                "status": "blocked",
                "reason": modelFit.get("modelType"),
            }
        ]
    latest = _latestUsable(panel) or {}
    recent_growth = _number(assumptions.get("recentGrowthPct"))
    normalized_roc = _number(assumptions.get("normalizedRocPct"))
    sales_to_capital = _number(assumptions.get("salesToCapital"))
    latest_reinvestment = _number(latest.get("reinvestmentRatePct"))
    latest_roc = _number(latest.get("rocPct"))
    reverse_growth = _number(reverse.get("requiredGrowthPct"))
    implied_by_latest = (
        latest_reinvestment * latest_roc / 100.0 if latest_reinvestment is not None and latest_roc is not None else None
    )
    required_reinvestment = (
        recent_growth / normalized_roc * 100.0
        if recent_growth is not None and normalized_roc is not None and normalized_roc > 0
        else None
    )
    incremental_roc = _incrementalRoc(panel)

    status = "usable"
    if reverse.get("status") == "blocked":
        status = "partialNoMarketCap"
    elif reverse_growth is not None and recent_growth is not None and reverse_growth - recent_growth > 5.0:
        status = "stretched"

    return [
        {"metric": "growthFeasibility", "value": status, "status": status},
        {"metric": "recentGrowthPct", "value": _round(recent_growth, 2), "status": "evidence"},
        {
            "metric": "growthFromLatestReinvestmentPct",
            "value": _round(implied_by_latest, 2),
            "status": "evidence",
        },
        {
            "metric": "requiredReinvestmentRatePct",
            "value": _round(required_reinvestment, 2),
            "status": "evidence",
        },
        {"metric": "normalizedRocPct", "value": _round(normalized_roc, 2), "status": "evidence"},
        {"metric": "incrementalRocPct", "value": _round(incremental_roc, 2), "status": "evidence"},
        {"metric": "salesToCapital", "value": _round(sales_to_capital, 3), "status": "evidence"},
        {
            "metric": "reverseRequiredGrowthPct",
            "value": _round(reverse_growth, 2),
            "status": reverse.get("status", "unknown"),
        },
    ]


def _costOfCapitalTable(assumptions: dict[str, Any]) -> list[dict[str, Any]]:
    keys = (
        "riskFreeRatePct",
        "erpPct",
        "beta",
        "costOfEquityPct",
        "afterTaxCostOfDebtPct",
        "debtToCapitalPct",
        "waccPct",
        "terminalGrowthPct",
    )
    return [{"assumption": key, "value": _round(assumptions.get(key), 3)} for key in keys]


def _dcfTable(dcf: dict[str, Any]) -> list[dict[str, Any]]:
    if dcf.get("status") == "blocked":
        return [{"case": "blocked", "reason": dcf.get("reason")}]
    return [
        {
            "case": case,
            "growthPct": dcf[case].get("growthPct"),
            "marginPct": dcf[case].get("marginPct"),
            "waccPct": dcf[case].get("waccPct"),
            "equityValue": dcf[case].get("equityValue"),
            "perShare": dcf[case].get("perShare"),
            "upsidePct": dcf[case].get("upsidePct"),
            "terminalValueSharePct": dcf[case].get("terminalValueSharePct"),
        }
        for case in ("bear", "base", "bull")
        if case in dcf
    ]


def _scenarioTable(dcf: dict[str, Any], reverse: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _dcfTable(dcf)
    rows.append(
        {
            "case": "reverseDcf",
            "requiredGrowthPct": reverse.get("requiredGrowthPct"),
            "normalizedGrowthPct": reverse.get("normalizedGrowthPct"),
            "plausibility": reverse.get("plausibility"),
            "status": reverse.get("status"),
        }
    )
    return rows


def _deepDiveTable(
    decisionStatus: str,
    modelFit: dict[str, Any],
    dcf: dict[str, Any],
    reverse: dict[str, Any],
    gaps: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {"step": "dataAudit", "status": "usableWithFallback" if gaps else "usable"},
        {
            "step": "businessModelFit",
            "status": modelFit.get("modelType"),
            "eligible": modelFit.get("genericFcffEligible"),
        },
        {"step": "fcffDcf", "status": dcf.get("status", "usable")},
        {"step": "scenarioFalsifier", "status": reverse.get("status", "usable")},
        {"step": "finalDecision", "status": decisionStatus, "gapCount": len(gaps)},
    ]


def _sources(countryDefaults: dict[str, Any], industryDefaults: dict[str, Any]) -> list[dict[str, str]]:
    urls = industryDefaults.get("_meta", {}).get("sourceUrls") or {}
    out = [
        {
            "id": "damodaranCountryRiskPremiums",
            "title": "Damodaran Country Risk Premiums",
            "url": str(countryDefaults.get("_meta", {}).get("url") or ""),
        }
    ]
    for key, url in urls.items():
        out.append({"id": f"damodaranIndustry_{key}", "title": f"Damodaran industry {key}", "url": str(url)})
    return out


def _latestUsable(panel: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in panel:
        if row.get("revenue") is not None and row.get("ebit") is not None:
            return row
    return panel[0] if panel else None


def _growth(current: Any, previous: Any) -> float | None:
    current_f = _number(current)
    previous_f = _number(previous)
    if current_f is None or previous_f is None or previous_f <= 0:
        return None
    return current_f / previous_f - 1.0


def _median(values: list[Any]) -> float | None:
    nums = [_number(value) for value in values]
    clean = [value for value in nums if value is not None]
    if not clean:
        return None
    return float(statistics.median(clean))


def _incrementalRoc(panel: list[dict[str, Any]]) -> float | None:
    chronological = sorted(panel, key=lambda row: str(row.get("year") or ""))
    values: list[float] = []
    for previous, current in zip(chronological, chronological[1:]):
        current_nopat = _number(current.get("nopat"))
        previous_nopat = _number(previous.get("nopat"))
        current_capital = _number(current.get("investedCapital"))
        previous_capital = _number(previous.get("investedCapital"))
        if None in (current_nopat, previous_nopat, current_capital, previous_capital):
            continue
        delta_capital = current_capital - previous_capital
        if delta_capital <= 0:
            continue
        values.append((current_nopat - previous_nopat) / delta_capital * 100.0)
    return _median(values)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pct(value: float | None) -> float | None:
    return _round(value * 100.0, 2) if value is not None else None


def _round(value: Any, digits: int = 0) -> float | None:
    num = _number(value)
    if num is None:
        return None
    return round(num, digits)


def _roundRow(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, float):
            digits = 3 if key in {"salesToCapital"} else 2 if key.endswith("Pct") else 0
            out[key] = _round(value, digits)
        else:
            out[key] = value
    return out


__all__ = ["buildDamodaranMemo"]
