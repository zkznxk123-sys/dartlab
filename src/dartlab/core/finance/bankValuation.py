"""Bank Excess Return Model — Damodaran *Investment Valuation* Ch.21.

은행/금융지주 전용 가치평가:
    Equity Value = Book Equity + Σ[(ROE - Ke) × Book Equity × growth^t] / (Ke - g)

은행은 CapEx 거의 없음 → 일반 DCF 부적합.
Book Equity 가 의사 CapEx 역할 → Excess Return Model 표준.

Damodaran 한국 은행 PBR 표준: 0.5~1.0 (저금리 + 신용리스크 반영).
"""

from __future__ import annotations


def calcBankExcessReturn(
    bookEquity: float,
    roe: float,
    costOfEquity: float,
    growthRate: float = 2.0,
    *,
    excessReturnYears: int = 10,
) -> dict:
    """Damodaran Bank Excess Return Model.

    Equity Value = Book Equity + Σ[(ROE - Ke) × BV × g^t] / (Ke - g)

    Parameters
    ----------
    bookEquity : 자기자본 (원)
    roe : 자기자본수익률 (%, 0~30 정상 범위)
    costOfEquity : Cost of Equity Ke (%, CAPM)
    growthRate : 영구성장률 (%) — 한국 은행 권고 1.5~2.5%
    excessReturnYears : explicit Excess Return 구간 연수 (기본 10)

    Returns
    -------
    dict
        bookEquity, roe, costOfEquity, growthRate
        excessReturn : 연간 Excess Return (원)
        pvExplicit : explicit n년 현가 합
        pvTerminal : Terminal Excess Return 현가
        equityValue : Book + pvExplicit + pvTerminal
        impliedPBR : equityValue / bookEquity
        method : "excess_return"
        warnings : list[str]
    """
    warnings: list[str] = []

    if bookEquity is None or bookEquity <= 0:
        return {"method": "skip", "warnings": ["Book Equity ≤ 0 — Excess Return 부적합"], "equityValue": None}

    if roe is None or costOfEquity is None or costOfEquity <= 0:
        return {"method": "skip", "warnings": ["ROE/Ke 부재"], "equityValue": None}

    # 입력 정규화
    roe_dec = float(roe) / 100.0
    ke_dec = float(costOfEquity) / 100.0
    g_dec = float(growthRate) / 100.0

    # TG 보정 (Damodaran 권고: g < Ke)
    if g_dec >= ke_dec:
        old_g = g_dec * 100
        g_dec = max(0.01, ke_dec - 0.02)
        warnings.append(f"영구성장률 {old_g:.1f}% ≥ Ke {ke_dec*100:.1f}% → {g_dec*100:.1f}%로 보정")

    # Excess Return = (ROE - Ke) × Book Equity
    annual_excess = (roe_dec - ke_dec) * bookEquity

    # explicit n년 + terminal (각 해 BV growth_rate 적용)
    pv_explicit = 0.0
    bv_t = bookEquity
    for yr in range(1, excessReturnYears + 1):
        bv_t = bv_t * (1.0 + g_dec)
        excess_t = (roe_dec - ke_dec) * bv_t
        pv_t = excess_t / ((1.0 + ke_dec) ** yr)
        pv_explicit += pv_t

    # Terminal: Excess Return 영구 지속 가정 (일부 banks: terminal=0 보수적)
    terminal_excess = (roe_dec - ke_dec) * bv_t * (1.0 + g_dec)
    pv_terminal = (terminal_excess / (ke_dec - g_dec)) / ((1.0 + ke_dec) ** excessReturnYears)

    equity_value = bookEquity + pv_explicit + pv_terminal
    implied_pbr = equity_value / bookEquity if bookEquity > 0 else None

    # Sanity: PBR 음수 또는 5배 초과 → 경고
    if implied_pbr is not None and implied_pbr < 0:
        warnings.append(f"impliedPBR {implied_pbr:.2f} < 0 — ROE < Ke 영구 가정")
    elif implied_pbr is not None and implied_pbr > 5.0:
        warnings.append(f"impliedPBR {implied_pbr:.2f} > 5x — ROE-Ke spread 과대")

    return {
        "bookEquity": bookEquity,
        "roe": round(roe, 2),
        "costOfEquity": round(costOfEquity, 2),
        "growthRate": round(g_dec * 100, 2),
        "excessReturnYears": excessReturnYears,
        "excessReturn": round(annual_excess, 0),
        "pvExplicit": round(pv_explicit, 0),
        "pvTerminal": round(pv_terminal, 0),
        "equityValue": round(equity_value, 0),
        "impliedPBR": round(implied_pbr, 3) if implied_pbr is not None else None,
        "method": "excess_return",
        "warnings": warnings,
    }
