"""은행/금융지주 전용 dFV — Damodaran Ch.21 Bank Excess Return 통합.

detection: c.sector.sector == "금융" 또는 industryGroup in {"은행","금융지주","증권","보험"}
"""

from __future__ import annotations

from typing import Any

_FINANCIAL_SECTOR_KEYWORDS = ("금융", "Financial", "FINANCIALS", "Bank")
_FINANCIAL_GROUP_KEYWORDS = (
    "은행",
    "금융지주",
    "증권",
    "보험",
    "신용카드",
    "BANK",
    "INSURANCE",
    "BROKERAGE",
    "Bank",
    "Insurance",
)


def isFinancialCompany(company: Any) -> bool:
    """sector/industryGroup 기반 금융업 검출 (Enum/str 모두 처리).

    Parameters
    ----------
    company : Company
        판별 대상 기업.

    Returns
    -------
    bool
        금융업이면 True.
    """
    sector = getattr(company, "sector", None)
    if sector is None:
        return False
    sec_raw = getattr(sector, "sector", "")
    grp_raw = getattr(sector, "industryGroup", "")
    sec_str = str(sec_raw) if sec_raw is not None else ""
    grp_str = str(grp_raw) if grp_raw is not None else ""
    for kw in _FINANCIAL_SECTOR_KEYWORDS:
        if kw in sec_str:
            return True
    for kw in _FINANCIAL_GROUP_KEYWORDS:
        if kw in grp_str:
            return True
    # 종목명 fallback
    name = getattr(company, "corpName", "") or getattr(company, "name", "") or ""
    return any(kw in name for kw in ("금융", "은행", "증권", "보험", "카드"))


def calcBankDFV(company: Any, *, basePeriod: str | None = None, overrides: dict | None = None) -> dict | None:
    """은행 전용 dFV — Excess Return Model.

    Returns
    -------
    dict (calcDFV 호환 스키마)
        dFV, scenarios, currentPrice, upside, opinion, confidence
        primaryModel : "bankExcessReturn"
        bankModel : detail dict (impliedPBR, excessReturn, ...)
    """
    try:
        from dartlab.analysis.valuation.bankValuation import calcBankExcessReturn
        from dartlab.core.overrides import applyOverride
        from dartlab.core.utils.helpers import toDictBySnakeId
        from dartlab.macro.rates.riskPremiums import loadDamodaranERP
    except ImportError:
        return None

    overrides = overrides or {}

    # Book Equity 추출 (BS)
    book_equity: float | None = None
    shares: int | None = None
    try:
        bs = company.select("BS", ["자본총계"])
        parsed = toDictBySnakeId(bs)
        if parsed:
            data, periods = parsed
            if periods:
                latest = periods[0]
                eq_row = data.get("total_stockholders_equity") or {}
                v = eq_row.get(latest)
                if v and v > 0:
                    book_equity = float(v)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    if not book_equity:
        return None

    # ROE 추출 (당기순이익 / 자본총계)
    net_income: float | None = None
    try:
        income = company.select("IS", ["당기순이익"])
        is_parsed = toDictBySnakeId(income)
        if is_parsed:
            is_data, is_periods = is_parsed
            if is_periods:
                ni_row = is_data.get("net_profit") or is_data.get("net_income") or {}
                v = ni_row.get(is_periods[0])
                if v:
                    net_income = float(v)
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    if not net_income or net_income <= 0:
        return None

    roe_pct = net_income / book_equity * 100  # 한국 은행 일반 5~12%

    # Cost of Equity (CAPM, 은행 beta 0.95 기본)
    currency = getattr(company, "currency", "KRW")
    country = applyOverride(None, "countryCode", overrides)
    erp = loadDamodaranERP(countryCode=country, currency=currency)
    rf = erp["riskFreeRate"]
    market_erp = erp["totalERP"]
    bank_beta = 0.95  # Damodaran 한국 은행 평균
    ke = rf + bank_beta * market_erp

    # 영구성장률 — Damodaran 권고 GDP 근접 2%
    g = applyOverride(2.0, "terminalGrowth", overrides)

    # Excess Return Model 호출
    bank = calcBankExcessReturn(
        bookEquity=book_equity,
        roe=roe_pct,
        costOfEquity=ke,
        growthRate=g,
        excessReturnYears=10,
    )

    if bank.get("method") == "skip" or not bank.get("equityValue"):
        return None

    # shares 역산 — calcDcf 우선, 실패 시 calcRelativeValuation/시가총액
    try:
        from dartlab.analysis.financial.valuation import calcDcf

        dcf_result = calcDcf(company)
        if isinstance(dcf_result, dict):
            eq = dcf_result.get("equityValue")
            ps = dcf_result.get("perShareValue")
            if eq and ps and ps > 0:
                shares = int(eq / ps)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    if not shares:
        try:
            from dartlab.analysis.financial.valuation import calcRelativeValuation

            rel = calcRelativeValuation(company)
            if isinstance(rel, dict):
                cur_p = rel.get("currentPrice")
                if cur_p and cur_p > 0:
                    # market cap 추정: relative consensusValue × shares = book proxy
                    # → shares = book_equity / (book per share). 보수적: 발행주식수 = book × PBR_target / current_price
                    # 더 단순: gather price 결과 시총 / current_price
                    pass
        except (ImportError, AttributeError, ValueError, TypeError):
            pass
    if not shares:
        # 최후 fallback: book equity 의 PBR 0.8 가정 시 시총 추정 → shares
        cur_p = _getCurrentPriceLight(company)
        if cur_p and cur_p > 0:
            estimated_market_cap = book_equity * 0.85  # 한국 은행 평균 PBR 0.85
            shares = int(estimated_market_cap / cur_p)

    if not shares or shares <= 0:
        return None

    per_share = bank["equityValue"] / shares
    if per_share <= 0:
        return None

    # 현재가 + upside
    currentPrice = _getCurrentPriceLight(company)
    upside = (per_share - currentPrice) / currentPrice * 100 if currentPrice and currentPrice > 0 else None

    opinion = _opinion(upside)
    confidence = "medium" if abs(upside or 0) < 30 else "low"

    bull = per_share * 1.15
    bear = per_share * 0.85

    return {
        "dFV": round(per_share),
        "scenarios": {"bull": round(bull), "base": round(per_share), "bear": round(bear)},
        "currentPrice": round(currentPrice) if currentPrice else None,
        "upside": round(upside, 1) if upside is not None else None,
        "opinion": opinion,
        "confidence": confidence,
        "primaryModel": "bankExcessReturn",
        "companyType": "금융",
        "lifeCyclePhase": "matureStable",
        "bankModel": {
            "bookEquity": book_equity,
            "roe": round(roe_pct, 2),
            "costOfEquity": round(ke, 2),
            "impliedPBR": bank["impliedPBR"],
            "excessReturn": bank["excessReturn"],
            "pvExplicit": bank["pvExplicit"],
            "pvTerminal": bank["pvTerminal"],
            "warnings": bank["warnings"],
        },
        "qualityWACC": {"baseWACC": ke, "adjustedWACC": ke, "totalSpread": 0, "factors": []},
        "allMethods": {"bankExcessReturn": round(per_share)},
        "triangulation": {"checks": [], "confidence": confidence},
    }


def _getCurrentPriceLight(company: Any) -> float | None:
    """현재 주가 추출 — currentPrice 속성 우선, 없으면 gather 경유.

    Returns
    -------
    float | None
        현재 주가 (원). 조회 실패 시 None.
    """
    try:
        price = getattr(company, "currentPrice", None)
        if price:
            return float(price)
        from dartlab.core.di import getMacroProvider

        g = getMacroProvider().getDefaultGather()
        p = g("price", getattr(company, "stockCode", ""))
        if p is not None and hasattr(p, "height") and p.height > 0:
            return float(p["close"][-1])
    except (ImportError, AttributeError, ValueError, TypeError, KeyError):
        pass
    return None


def _opinion(upside: float | None) -> str:
    """upside 기반 투자 의견 산출.

    Returns
    -------
    str
        "강력매수" | "매수" | "보유" | "매도" | "강력매도" | "판단 불가".
    """
    if upside is None:
        return "판단 불가"
    if upside > 30:
        return "강력매수"
    if upside > 10:
        return "매수"
    if upside > -10:
        return "보유"
    if upside > -30:
        return "매도"
    return "강력매도"
