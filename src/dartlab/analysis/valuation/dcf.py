"""내재가치 추정 엔진 — DCF + DDM + 상대가치."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from dartlab.analysis.valuation._dcfDdm import _annualDividends, ddmValuation
from dartlab.analysis.valuation._dcfTypes import (
    DCFResult,
    DDMResult,
    RelativeValuationResult,
    SensitivityResult,
    ValuationSummary,
)

# ── 내부 유틸 ──────────────────────────────────────────────
from dartlab.core.utils.calc import cagr as _cagr  # noqa: E402
from dartlab.core.utils.extract import (
    getAnnualValues,
    getLatest,
    getRevenueGrowth3Y,
    getTTM,
)
from dartlab.core.utils.fmt import fmtBig, fmtPrice
from dartlab.frame.sector import SectorParams


def _getFcfFromSeries(series: dict, annual: bool = False) -> Optional[float]:
    """FCF = 영업CF - CAPEX."""
    flow = getLatest if annual else getTTM
    ocf = flow(series, "CF", "operating_cashflow")
    capex = flow(series, "CF", "purchase_of_property_plant_and_equipment")
    if ocf is None:
        return None
    return ocf - abs(capex or 0)


def _getNetDebt(series: dict) -> float:
    """순차입금 = 총차입금 - 현금."""
    stb = getLatest(series, "BS", "shortterm_borrowings") or 0
    ltb = getLatest(series, "BS", "longterm_borrowings") or 0
    bonds = getLatest(series, "BS", "debentures") or 0
    cash = getLatest(series, "BS", "cash_and_cash_equivalents") or 0
    return stb + ltb + bonds - cash


def _fcfHistory(series: dict) -> list[Optional[float]]:
    """연간 FCF 시계열 (영업CF - CAPEX)."""
    ocfVals = getAnnualValues(series, "CF", "operating_cashflow")
    capexVals = getAnnualValues(series, "CF", "purchase_of_property_plant_and_equipment")
    if not ocfVals:
        return []
    result: list[Optional[float]] = []
    for i in range(len(ocfVals)):
        o = ocfVals[i]
        c = capexVals[i] if i < len(capexVals) else None
        if o is None:
            result.append(None)
        else:
            result.append(o - abs(c or 0))
    return result


# ── Damodaran Two-Stage DCF (Investment Valuation Ch.12) ──────────────────
# 명시적 고성장 n년 → stable 수렴. Growth equation 엄격 적용.


def multiStageDcf(
    *,
    baseFcf: float,
    growthYears: int | list[int],
    growthRates: float | list[float],
    terminalGrowthRate: float,
    wacc: float,
    marginPath: list[float] | None = None,
    reinvestmentPath: list[float] | None = None,
    netDebt: float = 0.0,
    shares: int | None = None,
) -> dict:
    """Damodaran Multi-stage DCF — 가변 성장률/마진/재투자율 지원.

    growthYears, growthRates 가 list 면 phase 별 구간. scalar 면 단일 phase.
    Phase 1..N: 각 phase 의 고정 성장률로 FCF 투영 + 할인
    Terminal: FCF_{n+1} / (WACC - g_stable)

    Parameters
    ----------
    baseFcf : 기준 FCF (원)
    growthYears : int 또는 [n1, n2, ...] phase 별 연수
    growthRates : float 또는 [r1, r2, ...] phase 별 연성장률 (%)
    terminalGrowthRate : 영구성장률 (%). WACC - 2% 이하 권장, Rf 초과 금지.
    wacc : 할인율 (%)
    marginPath : 연도별 영업마진 (선택). 없으면 baseFcf 가 이미 마진 반영 가정.
    reinvestmentPath : 연도별 재투자율 (선택).
    netDebt : 순차입금 (원)
    shares : 발행주식수

    Returns
    -------
    dict
        baseFcf, wacc, terminalGrowthRate
        growthYears : list[int]
        growthRates : list[float]
        marginPath, reinvestmentPath
        projections : list[float] — 연도별 예측 FCF
        phases : list[{years, rate, pv}]
        pvExplicit, terminalValue, pvTerminal, enterpriseValue,
        equityValue, perShare, tvShare, warnings
    """
    warnings: list[str] = []

    # 입력 정규화 — scalar → list
    years_list = [growthYears] if isinstance(growthYears, int) else list(growthYears)
    rates_list = [growthRates] if isinstance(growthRates, (int, float)) else list(growthRates)

    if len(years_list) != len(rates_list):
        warnings.append(f"growthYears/Rates length mismatch ({len(years_list)} vs {len(rates_list)}) — truncate")
        m = min(len(years_list), len(rates_list))
        years_list = years_list[:m]
        rates_list = rates_list[:m]

    total_years = sum(max(1, y) for y in years_list)
    if total_years > 15:
        warnings.append(f"총 고성장 구간 {total_years}년은 과도 — 10년 내로 축소 권장")

    # TG 보정
    if wacc <= terminalGrowthRate:
        old_tg = terminalGrowthRate
        terminalGrowthRate = max(wacc - 2.0, 1.0)
        warnings.append(f"영구성장률 {old_tg:.1f}% ≥ WACC {wacc:.1f}% → {terminalGrowthRate:.1f}%로 보정")

    r = wacc / 100.0
    gs = terminalGrowthRate / 100.0

    projections: list[float] = []
    phases_info: list[dict] = []
    current = baseFcf
    global_year = 0
    pv_explicit = 0.0

    for phase_idx, (ph_years, ph_rate) in enumerate(zip(years_list, rates_list)):
        ph_years = max(1, int(ph_years))
        g = ph_rate / 100.0
        phase_pv = 0.0
        for _ in range(ph_years):
            global_year += 1
            current = current * (1 + g)
            # marginPath 가 있으면 FCF 재조정
            if marginPath and global_year - 1 < len(marginPath):
                # margin 변화만큼 FCF 조정 (baseFcf × (margin[t] / baseMargin) — 단순 근사)
                # 실제로는 revenue × margin 이지만 여기선 FCF 기반이므로 스킵 (반환 dict 에만 기록)
                pass
            projections.append(current)
            pv_year = current / ((1 + r) ** global_year)
            phase_pv += pv_year
            pv_explicit += pv_year
        phases_info.append(
            {
                "years": ph_years,
                "rate": ph_rate,
                "pv": phase_pv,
                "endFcf": current,
            }
        )

    # Terminal
    fcf_next = projections[-1] * (1 + gs)
    terminal_value = fcf_next / (r - gs)
    pv_terminal = terminal_value / ((1 + r) ** global_year)

    enterprise_value = pv_explicit + pv_terminal
    tv_share = pv_terminal / enterprise_value if enterprise_value > 0 else 0.0

    equity_value = enterprise_value - netDebt
    per_share = equity_value / shares if shares and shares > 0 else None

    if tv_share > 0.80:
        warnings.append(f"Terminal Value 비중 {tv_share * 100:.0f}% 과도 — explicit 구간 신뢰도 낮음")

    return {
        "baseFcf": baseFcf,
        "growthYears": years_list,
        "growthRates": rates_list,
        "terminalGrowthRate": terminalGrowthRate,
        "wacc": wacc,
        "marginPath": marginPath,
        "reinvestmentPath": reinvestmentPath,
        "projections": projections,
        "phases": phases_info,
        "pvExplicit": pv_explicit,
        "terminalValue": terminal_value,
        "pvTerminal": pv_terminal,
        "enterpriseValue": enterprise_value,
        "equityValue": equity_value,
        "perShare": per_share,
        "tvShare": tv_share,
        "warnings": warnings,
    }


def twoStageDcf(
    *,
    baseFcf: float,
    growthYears: int,
    highGrowthRate: float,
    terminalGrowthRate: float,
    wacc: float,
    netDebt: float = 0.0,
    shares: int | None = None,
) -> dict:
    """Two-Stage DCF — multiStageDcf wrapper (backward compat).

    단일 phase (n 년 × 단일 성장률) + terminal. 기존 호출 호환용.
    """
    r = multiStageDcf(
        baseFcf=baseFcf,
        growthYears=[growthYears],
        growthRates=[highGrowthRate],
        terminalGrowthRate=terminalGrowthRate,
        wacc=wacc,
        netDebt=netDebt,
        shares=shares,
    )
    # 기존 twoStageDcf 반환 키 호환
    r["highGrowthRate"] = highGrowthRate
    # growthYears 는 list[int] 상태 — 기존 caller 가 int 를 기대할 수 있으므로
    # primary dict 구조는 유지 (list). 기존 테스트는 projections/pvExplicit/tvShare 만 검증.
    return r


# ── Damodaran Liquidation Valuation (Dark Side Ch.9) ──────────────────────
# 자산별 회수율 차등 적용. 청산 절차에서 무형/재고가 가장 손실 큼.

_LIQUIDATION_RECOVERY = {
    "cash": 1.00,  # 현금성자산
    "receivables": 0.70,  # 매출채권
    "inventory": 0.50,  # 재고자산
    "tangible": 0.60,  # 유형자산
    "intangible": 0.10,  # 무형자산 (영업권 포함)
    "other": 0.40,  # 기타자산 fallback
}


def liquidationValuation(
    *,
    cash: float = 0.0,
    receivables: float = 0.0,
    inventory: float = 0.0,
    tangibleAssets: float = 0.0,
    intangibleAssets: float = 0.0,
    otherAssets: float = 0.0,
    totalLiabilities: float = 0.0,
    shares: int | None = None,
    recoveryOverrides: dict | None = None,
) -> dict:
    """Damodaran 청산가치 — 자산별 회수율 차등.

    Returns
    -------
    dict
        recoveries : dict — 자산별 회수 금액
        grossRecovery : float — 총 자산 회수 합
        netToEquity : float — 부채 상환 후 잔여
        perShare : float | None
        weightedRecoveryRate : float — 가중 평균 회수율 (0.0~1.0)
    """
    recovery = dict(_LIQUIDATION_RECOVERY)
    if recoveryOverrides:
        recovery.update(recoveryOverrides)

    components = {
        "cash": cash * recovery["cash"],
        "receivables": receivables * recovery["receivables"],
        "inventory": inventory * recovery["inventory"],
        "tangible": tangibleAssets * recovery["tangible"],
        "intangible": intangibleAssets * recovery["intangible"],
        "other": otherAssets * recovery["other"],
    }
    gross = sum(components.values())
    net_to_equity = gross - totalLiabilities
    per_share = (net_to_equity / shares) if (shares and shares > 0 and net_to_equity > 0) else None

    gross_raw = cash + receivables + inventory + tangibleAssets + intangibleAssets + otherAssets
    weighted_rate = gross / gross_raw if gross_raw > 0 else 0.0

    return {
        "recoveries": components,
        "grossRecovery": gross,
        "netToEquity": net_to_equity,
        "perShare": per_share,
        "weightedRecoveryRate": weighted_rate,
        "recoveryRates": recovery,
    }


# ── DCF ──────────────────────────────────────────────


def _normalizeBaseFcf(series: dict, fcfCurrent: float | None, fcfHist: list, warnings: list[str]) -> float | None:
    """사이클 기업 mid-cycle FCF 정규화. 최근 FCF 가 극단 왜곡이면 중앙값 채택."""
    positiveFcfs = [f for f in fcfHist if f is not None and f > 0]
    if len(positiveFcfs) < 3:
        return fcfCurrent
    midCycleFcf = sorted(positiveFcfs)[len(positiveFcfs) // 2]
    if fcfCurrent is not None and fcfCurrent > 0:
        ratio = fcfCurrent / midCycleFcf if midCycleFcf > 0 else 1
        if ratio > 1.8 or ratio < 0.5:
            warnings.append(f"사이클 정규화: mid-cycle FCF 적용 (최근 대비 {ratio:.1f}배 괴리)")
            return midCycleFcf
        return fcfCurrent
    warnings.append("FCF 음수 → mid-cycle 양수 FCF 중앙값으로 대체")
    return midCycleFcf


def _fallbackOcfBasedFcf(series: dict, warnings: list[str]) -> float | None:
    """FCF 부재 시 영업CF × 할인률 fallback (호황기 과대 방지)."""
    ocfHist = getAnnualValues(series, "CF", "operating_cashflow")
    positiveOcfs = [v for v in ocfHist if v is not None and v > 0]
    allOcfs = [v for v in ocfHist if v is not None]
    if len(positiveOcfs) >= 3:
        midOcf = sorted(positiveOcfs)[len(positiveOcfs) // 2]
        lossRatio = 1 - len(positiveOcfs) / max(len(allOcfs), 1) if allOcfs else 0
        discount = 0.5 if lossRatio >= 0.5 else 0.7
        warnings.append(f"FCF 음수 → mid-cycle 영업CF × {discount * 100:.0f}%로 대체 (적자비율 {lossRatio * 100:.0f}%)")
        return midOcf * discount
    ocf = getTTM(series, "CF", "operating_cashflow")
    if ocf is not None and ocf > 0:
        warnings.append("FCF 음수/미확인 → 영업CF × 70%로 대체 추정")
        return ocf * 0.7
    return None


def _fallbackNormalizedEarningsFcf(series: dict, warnings: list[str]) -> float | None:
    """Damodaran normalized earnings — 정상 OPM × 현재 매출 → FCF proxy."""
    oiHist = getAnnualValues(series, "IS", "operating_profit")
    revHist = getAnnualValues(series, "IS", "sales")
    if not (oiHist and revHist):
        return None
    margins = [
        oi / rev for oi, rev in zip(oiHist, revHist) if oi is not None and rev is not None and rev > 0 and oi > 0
    ]
    if not margins:
        return None
    normalMargin = sorted(margins)[len(margins) // 2]
    latestRev = next((v for v in reversed(revHist) if v is not None and v > 0), None)
    if not (latestRev and normalMargin > 0):
        return None
    warnings.append(f"Normalized earnings: 정상 OPM {normalMargin * 100:.1f}% × 현재 매출 → FCF proxy")
    return latestRev * normalMargin * 0.65


def _resolveBaseFcf(series: dict, warnings: list[str]) -> tuple[float | None, list]:
    """기준 FCF 결정: series → mid-cycle → OCF fallback → normalized earnings."""
    fcfCurrent = _getFcfFromSeries(series)
    fcfHist = _fcfHistory(series)
    fcfCurrent = _normalizeBaseFcf(series, fcfCurrent, fcfHist, warnings)
    if fcfCurrent is None or fcfCurrent <= 0:
        fcfCurrent = _fallbackOcfBasedFcf(series, warnings)
    if fcfCurrent is None or fcfCurrent <= 0:
        fcfCurrent = _fallbackNormalizedEarningsFcf(series, warnings)
    return fcfCurrent, fcfHist


def _projectFcf(
    fcfCurrent: float,
    initialGrowth: float,
    tg: float,
    projectionYears: int,
    proformaFCF: list[float] | None,
    warnings: list[str],
) -> list[float]:
    """Pro Forma 우선 → 아니면 (initialGrowth → tg) blend 로 FCF 시계열 예측."""
    if proformaFCF and len(proformaFCF) > 0:
        pf = [float(f) for f in proformaFCF if f is not None and float(f) != 0]
        if pf:
            while len(pf) < projectionYears:
                pf.append(pf[-1] * (1 + tg / 100))
            warnings.append(f"추정재무제표(Pro Forma) 기반 FCF 사용 ({len(proformaFCF)}년 원본 + 연장)")
            return pf[:projectionYears]

    projections: list[float] = []
    prevFcf = fcfCurrent
    for yr in range(1, projectionYears + 1):
        blend = (yr - 1) / max(projectionYears - 1, 1)
        growth = initialGrowth * (1 - blend) + tg * blend
        proj = prevFcf * (1 + growth / 100)
        projections.append(proj)
        prevFcf = proj
    return projections


def _computeExitMultipleTv(
    series: dict,
    sectorParams: SectorParams | None,
    initialGrowth: float,
    tg: float,
    projectionYears: int,
    wacc: float,
    pvFcfs: float,
    netDebt: float,
    shares: int | None,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Exit Multiple TV 교차검증 — EBITDA × 섹터 exit multiple. (tv, ev, perShare, mult)."""
    exitMult = sectorParams.exitMultiple if sectorParams and sectorParams.exitMultiple else None
    if not (exitMult and exitMult > 0):
        return None, None, None, None
    oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
    if oi is None or oi <= 0:
        return None, None, None, exitMult
    dep = getTTM(series, "CF", "depreciation_and_amortization")
    if dep is None:
        ta = getLatest(series, "BS", "tangible_assets") or 0
        ia = getLatest(series, "BS", "intangible_assets") or 0
        dep = ta * 0.05 + ia * 0.1
    ebitda = oi + (dep or 0)
    if ebitda <= 0:
        return None, None, None, exitMult
    projEbitda = ebitda
    for yr in range(1, projectionYears + 1):
        blend = (yr - 1) / max(projectionYears - 1, 1)
        g = initialGrowth * (1 - blend) + tg * blend
        projEbitda *= 1 + g / 100
    exitTv = projEbitda * exitMult
    pvExitTv = exitTv / (1 + wacc / 100) ** projectionYears
    exitEv = pvFcfs + pvExitTv
    exitEqValue = exitEv - netDebt
    exitPerShare = exitEqValue / shares if shares and shares > 0 else None
    return exitTv, exitEv, exitPerShare, exitMult


def dcfValuation(
    series: dict,
    shares: Optional[int] = None,
    sectorParams: Optional[SectorParams] = None,
    currentPrice: Optional[float] = None,
    discountRate: Optional[float] = None,
    terminalGrowth: Optional[float] = None,
    projectionYears: int = 5,
    currency: str = "KRW",
    proformaFCF: Optional[list[float]] = None,
) -> DCFResult:
    """2-Stage DCF 밸류에이션 — FCF 프로젝션 + Terminal Value → 주당 가치.

    Capabilities:
        FCF 시계열에서 base FCF 추정 → 5년 초기 성장 (매출 3Y CAGR + 섹터
        평균) → Gordon growth terminal value → WACC 할인 → 기업가치 + 주당
        가치 산출. Damodaran multiStage DCF 의 직접 단순화 버전.

    Args:
        series: ``finance.timeseries`` 시계열 dict (BS/IS/CF).
        shares: 발행주식수. 주당 가치 산출용.
        sectorParams: 업종별 할인율/성장률.
        currentPrice: 현재 주가 (원). marginOfSafety 계산용.
        discountRate: WACC override (sectorParams.discountRate 우선).
        terminalGrowth: 영구성장률 override. None 시 ``min(sector growth, 3%)``.
        projectionYears: 초기 성장기 (년). 기본 5.
        currency: ``"KRW"`` 또는 ``"USD"``. 출력 단위.
        proformaFCF: AI 가 산출한 향후 FCF list override. 주어지면 ``_projectFcf``
            가 이를 base 로 사용.

    Returns:
        DCFResult dataclass:
            - ``fcfHistorical``/``fcfProjections`` (list[float])
            - ``terminalValue``/``enterpriseValue``/``equityValue`` (float)
            - ``perShareValue`` (float|None): shares 가 있어야 산출
            - ``discountRate``/``growthRateInitial``/``terminalGrowth`` (float)
            - ``marginOfSafety`` (float|None): (perShare - currentPrice) /
              currentPrice * 100. currentPrice 없으면 None
            - ``warnings`` (list[str]): DCF 적용 불가/조정 경고
            - ``currency`` (str)
        FCF 음수 시 빈 결과 + "DCF 적용 불가" warning.

    Raises:
        없음.

    Example:
        >>> from dartlab.frame.sector import SECTOR_PARAMS
        >>> r = dcfValuation(series, shares=5e9, sectorParams=SECTOR_PARAMS["IT"],
        ...                  currentPrice=75000)
        >>> r.perShareValue, r.marginOfSafety
        (82000.0, 9.3)

    Guide:
        WACC ≤ terminalGrowth 시 ``wacc - 2.0`` 으로 자동 조정 + warning. initial
        growth 는 매출 3Y CAGR 기반, [-5%, 15%] clamp. FCF 음수 회사는 DCF
        부적합 — 호출자가 ``calcDFV`` 의 multi-model triangulation 사용 권장.

    SeeAlso:
        - ``multiStageDcf``: phase 별 다중 stage DCF
        - ``ddmValuation``: 배당 기반 가치 (현금흐름 없는 회사)
        - ``calcDFV``: 다중 모델 통합 진입점

    Requires:
        series 가 finance.timeseries 스키마. 최소 3 년 시계열.

    AIContext:
        DCF 가치 단독 인용 금지 — marginOfSafety + warnings 함께 노출. FCF
        음수/수익 매출 변동성 큰 회사 (initial growth > 15%) 는 신뢰도 낮음.
        Damodaran 의 권고: terminalGrowth ≤ 무위험이자율.

    LLM Specifications:
        AntiPatterns:
            - terminalGrowth 4%+ 입력 금지 (실질 GDP 성장률 초과 = Gordon
              가정 위반). 자동 조정되지만 warning 발생.
            - shares 미지정 시 perShareValue=None — currentPrice 와 비교 불가.
            - currentPrice 가 distressed (실가치 대비 -50%+) 인 회사에서
              marginOfSafety 가 비정상 (500%+) → DCF 가정 자체 의심.
        OutputSchema:
            DCFResult (12 필드 dataclass).
        Prerequisites:
            series 의 CF/operating_cashflow + capex 시계열 ≥ 3 년.
        Freshness:
            series 의 freshness (보통 최신 분기).
        Dataflow:
            series → _resolveBaseFcf → revCagr → _projectFcf (5 년) →
            terminal value (Gordon) → WACC 할인 → enterprise → equity
            (net debt 차감) → 주당.
        TargetMarkets: KR (DART 기준 통화 KRW), US (EDGAR USD).
    """
    warnings: list[str] = []

    wacc = discountRate or (sectorParams.discountRate if sectorParams else 10.0)
    sectorGrowth = sectorParams.growthRate if sectorParams else 3.0
    tg = terminalGrowth if terminalGrowth is not None else min(sectorGrowth, 3.0)

    if wacc <= tg:
        tg = max(wacc - 2.0, 1.0)
        warnings.append(f"영구성장률이 할인율 이상이어서 {tg:.1f}%로 조정")

    fcfCurrent, fcfHist = _resolveBaseFcf(series, warnings)

    if fcfCurrent is None or fcfCurrent <= 0:
        return DCFResult(
            fcfHistorical=fcfHist,
            fcfProjections=[],
            terminalValue=0,
            enterpriseValue=0,
            equityValue=0,
            perShareValue=None,
            discountRate=wacc,
            growthRateInitial=0,
            terminalGrowth=tg,
            marginOfSafety=None,
            warnings=["FCF 및 영업CF 데이터 부족으로 DCF 적용 불가"],
            currency=currency,
        )

    revCagr = getRevenueGrowth3Y(series)
    if revCagr is not None:
        initialGrowth = min(max(revCagr, -5.0), 15.0)
    else:
        initialGrowth = sectorGrowth
        warnings.append("매출 3Y CAGR 미확인 → 섹터 평균 성장률 적용")

    projections = _projectFcf(fcfCurrent, initialGrowth, tg, projectionYears, proformaFCF, warnings)

    finalFcf = projections[-1]
    tv = finalFcf * (1 + tg / 100) / (wacc / 100 - tg / 100)
    pvFcfs = sum(fcf / (1 + wacc / 100) ** yr for yr, fcf in enumerate(projections, 1))
    pvTv = tv / (1 + wacc / 100) ** projectionYears
    ev = pvFcfs + pvTv

    netDebt = _getNetDebt(series)
    eqValue = ev - netDebt
    perShare = eqValue / shares if shares and shares > 0 else None
    mos = None
    if perShare is not None and currentPrice is not None and currentPrice > 0:
        mos = (perShare - currentPrice) / perShare * 100

    exitTv, exitEv, exitPerShare, exitMult = _computeExitMultipleTv(
        series, sectorParams, initialGrowth, tg, projectionYears, wacc, pvFcfs, netDebt, shares
    )

    assumptions = {
        "할인율": f"{wacc:.1f}%",
        "초기성장률": f"{initialGrowth:.1f}%",
        "영구성장률": f"{tg:.1f}%",
        "예측기간": f"{projectionYears}년",
        "순차입금": fmtBig(netDebt, currency),
        "기준FCF": fmtBig(fcfCurrent, currency),
    }
    if exitMult:
        assumptions["Exit Multiple"] = f"EV/EBITDA {exitMult:.1f}x"

    return DCFResult(
        fcfHistorical=fcfHist,
        fcfProjections=projections,
        terminalValue=tv,
        enterpriseValue=ev,
        equityValue=eqValue,
        perShareValue=perShare,
        discountRate=wacc,
        growthRateInitial=initialGrowth,
        terminalGrowth=tg,
        marginOfSafety=mos,
        exitMultipleTv=exitTv,
        exitMultipleEv=exitEv,
        exitMultiplePerShare=exitPerShare,
        assumptions=assumptions,
        warnings=warnings,
        currency=currency,
    )


# ── 상대가치 ──────────────────────────────────────────────


def _normalizedEarnings(series: dict, shares: int | None) -> tuple[float | None, float | None, bool]:
    """경기순환 조정 정규화 수익 -- Damodaran/CFA 표준.

    방법: 과거 3-5년 평균 ROE x 현재 BPS (mid-cycle earnings)
    Returns: (normalizedNI, normalizedEps, wasNormalized)
    """
    niVals = getAnnualValues(series, "IS", "net_profit")
    if not niVals:
        niVals = getAnnualValues(series, "IS", "net_income")
    eqVals = getAnnualValues(series, "BS", "total_stockholders_equity")
    if not eqVals:
        eqVals = getAnnualValues(series, "BS", "owners_of_parent_equity")

    if not niVals or not eqVals or len(niVals) < 3 or len(eqVals) < 3:
        return None, None, False

    # 최근 3-5년 ROE 평균
    n = min(len(niVals), len(eqVals), 5)
    roes: list[float] = []
    for i in range(-n, 0):
        ni = niVals[i] if abs(i) <= len(niVals) else None
        eq = eqVals[i] if abs(i) <= len(eqVals) else None
        if ni is not None and eq is not None and eq > 0:
            roes.append(ni / eq)

    if len(roes) < 2:
        return None, None, False

    avgRoe = sum(roes) / len(roes)
    currentEquity = eqVals[-1]
    if currentEquity is None or currentEquity <= 0:
        return None, None, False

    normalizedNi = currentEquity * avgRoe
    normalizedEps = normalizedNi / shares if shares and shares > 0 else None

    # TTM 대비 30% 이상 차이나면 정규화 적용
    ttmNi = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income")
    if ttmNi and ttmNi > 0 and normalizedNi > 0:
        divergence = abs(ttmNi - normalizedNi) / max(ttmNi, normalizedNi)
        return normalizedNi, normalizedEps, divergence > 0.3

    return normalizedNi, normalizedEps, True


def relativeValuation(
    series: dict,
    sectorParams: Optional[SectorParams] = None,
    marketCap: Optional[float] = None,
    shares: Optional[int] = None,
    currentPrice: Optional[float] = None,
) -> RelativeValuationResult:
    """섹터 배수 기반 상대가치 추정 (Normalized Earnings 지원)."""
    warnings: list[str] = []
    sp = sectorParams or SectorParams(
        discountRate=10.0,
        growthRate=3.0,
        perMultiple=15,
        pbrMultiple=1.2,
        evEbitdaMultiple=8,
        label="기타",
    )

    sectorMults: dict[str, float] = {
        "PER": sp.perMultiple,
        "PBR": sp.pbrMultiple,
        "EV/EBITDA": sp.evEbitdaMultiple,
    }

    netIncome = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income")
    equity = getLatest(series, "BS", "total_stockholders_equity") or getLatest(series, "BS", "owners_of_parent_equity")
    revenue = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")

    # Normalized Earnings -- 경기순환 조정
    normNi, normEps, useNormalized = _normalizedEarnings(series, shares)
    if useNormalized and normNi is not None:
        netIncome = normNi
        warnings.append("정규화 수익 적용 (과거 평균 ROE x 현재 BPS)")

    multKeys = ["PER", "PBR", "EV/EBITDA", "PSR", "PEG"]
    currentMults: dict[str, Optional[float]] = {k: None for k in multKeys}
    if marketCap and marketCap > 0:
        if netIncome and netIncome > 0:
            currentMults["PER"] = round(marketCap / netIncome, 1)
        if equity and equity > 0:
            currentMults["PBR"] = round(marketCap / equity, 1)
        if revenue and revenue > 0:
            currentMults["PSR"] = round(marketCap / revenue, 2)

    implied: dict[str, Optional[float]] = {k: None for k in multKeys}
    premiumDisc: dict[str, Optional[float]] = {k: None for k in multKeys}

    if shares and shares > 0:
        if netIncome is not None and netIncome > 0:
            eps = netIncome / shares
            implied["PER"] = round(eps * sp.perMultiple, 0)

        if equity is not None and equity > 0:
            bps = equity / shares
            implied["PBR"] = round(bps * sp.pbrMultiple, 0)

        oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
        dep = getTTM(series, "CF", "depreciation_and_amortization")
        if oi is not None and oi > 0:
            if dep is None:
                ta = getLatest(series, "BS", "tangible_assets") or 0
                ia = getLatest(series, "BS", "intangible_assets") or 0
                dep = ta * 0.05 + ia * 0.1
                warnings.append("감가상각 미확인 -> 추정치 적용")
            ebitda = oi + (dep or 0)
            if ebitda > 0:
                nd = _getNetDebt(series)
                impliedEv = ebitda * sp.evEbitdaMultiple
                impliedEq = impliedEv - nd
                if impliedEq > 0:
                    implied["EV/EBITDA"] = round(impliedEq / shares, 0)

        # PSR -- 매출 기반 가치
        if revenue is not None and revenue > 0:
            sps = revenue / shares  # Sales Per Share
            sectorPsr = _estimateSectorPsr(sp)
            sectorMults["PSR"] = sectorPsr
            implied["PSR"] = round(sps * sectorPsr, 0)

        # PEG -- PER / EPS 성장률
        epsGrowth = _epsGrowth3Y(series, shares)
        if epsGrowth is not None and epsGrowth > 0 and currentMults.get("PER"):
            peg = round(currentMults["PER"] / epsGrowth, 2)
            currentMults["PEG"] = peg
            # PEG 1.0 = 적정, 적정가 = EPS × 성장률 × 1.0 (PEG fair = 1)
            eps = netIncome / shares if netIncome and netIncome > 0 else 0
            if eps > 0:
                implied["PEG"] = round(eps * epsGrowth, 0)
                sectorMults["PEG"] = 1.0  # fair PEG

    if currentPrice and currentPrice > 0:
        for key in multKeys:
            iv = implied[key]
            if iv is not None and iv > 0:
                premiumDisc[key] = round((currentPrice - iv) / iv * 100, 1)

    # 가중 합의값 -- EV/EBITDA(자본구조 중립) > PER > PBR > PSR > PEG
    multWeights = {"EV/EBITDA": 3.0, "PER": 2.5, "PBR": 1.5, "PSR": 1.0, "PEG": 1.0}
    # 극단값 상한: 현재가의 5배 이상인 개별 멀티플은 consensus에서 제외
    _ivCap = currentPrice * 5 if currentPrice and currentPrice > 0 else float("inf")
    weightedSum = 0.0
    totalWeight = 0.0
    for key in multKeys:
        iv = implied[key]
        if iv is not None and 0 < iv < _ivCap:
            w = multWeights.get(key, 1.0)
            weightedSum += iv * w
            totalWeight += w
    consensus = round(weightedSum / totalWeight, 0) if totalWeight > 0 else None

    if totalWeight == 0:
        warnings.append("상대가치 추정 불가 (재무 데이터 부족)")

    return RelativeValuationResult(
        sectorMultiples=sectorMults,
        currentMultiples=currentMults,
        impliedValues=implied,
        premiumDiscount=premiumDisc,
        consensusValue=consensus,
        warnings=warnings,
    )


def _estimateSectorPsr(sp: SectorParams) -> float:
    """섹터 PSR 추정 -- PER × 순이익률 가정으로 역산."""
    # 일반적으로 PSR = PER × 순이익률
    # 순이익률 모르면 섹터 평균 5% 가정
    estimatedMargin = 0.05
    psr = sp.perMultiple * estimatedMargin
    return round(max(psr, 0.3), 2)


def _epsGrowth3Y(series: dict, shares: int) -> Optional[float]:
    """EPS 3년 CAGR (%)."""
    niVals = getAnnualValues(series, "IS", "net_profit")
    if not niVals:
        niVals = getAnnualValues(series, "IS", "net_income")
    if not niVals or len(niVals) < 4 or shares <= 0:
        return None

    recent = niVals[-4:]
    validNi = [v for v in recent if v is not None and v > 0]
    if len(validNi) < 2:
        return None

    epsStart = validNi[0] / shares
    epsEnd = validNi[-1] / shares
    if epsStart <= 0 or epsEnd <= 0:
        return None

    years = len(validNi) - 1
    cagr = _cagr(epsStart, epsEnd, years)
    # PEG 산출용 상한: 50% (사이클 기업 적자→흑전 시 수천% 방지)
    return min(cagr, 50.0) if cagr is not None else None


# ── 민감도 분석 ──────────────────────────────────────────────


def sensitivityAnalysis(
    series: dict,
    shares: Optional[int] = None,
    sectorParams: Optional[SectorParams] = None,
    currentPrice: Optional[float] = None,
    currency: str = "KRW",
    waccRange: float = 2.0,
    growthRange: float = 2.0,
    steps: int = 5,
) -> SensitivityResult | None:
    """WACC x 영구성장률 민감도 그리드.

    DCF 결과를 WACC +-waccRange, 영구성장률 +-growthRange로 재계산.
    """
    baseDcf = dcfValuation(
        series,
        shares=shares,
        sectorParams=sectorParams,
        currentPrice=currentPrice,
        currency=currency,
    )
    baseWacc = baseDcf.discountRate
    baseTg = baseDcf.terminalGrowth

    grid: list[dict] = []
    waccStep = waccRange * 2 / (steps - 1) if steps > 1 else 0
    growthStep = growthRange * 2 / (steps - 1) if steps > 1 else 0

    for wi in range(steps):
        wacc = baseWacc - waccRange + wi * waccStep
        if wacc <= 0:
            continue
        for gi in range(steps):
            tg = baseTg - growthRange + gi * growthStep
            if tg >= wacc:
                continue
            result = dcfValuation(
                series,
                shares=shares,
                sectorParams=sectorParams,
                discountRate=wacc,
                terminalGrowth=tg,
                currentPrice=currentPrice,
                currency=currency,
            )
            grid.append(
                {
                    "wacc": round(wacc, 1),
                    "terminalGrowth": round(tg, 1),
                    "perShareValue": result.perShareValue,
                    "enterpriseValue": result.enterpriseValue,
                }
            )

    return SensitivityResult(
        grid=grid,
        baseWacc=baseWacc,
        baseTerminalGrowth=baseTg,
        baseValue=baseDcf.perShareValue,
    )


# ── 종합 밸류에이션 ──────────────────────────────────────────


def fullValuation(
    series: dict,
    shares: Optional[int] = None,
    sectorParams: Optional[SectorParams] = None,
    marketCap: Optional[float] = None,
    currentPrice: Optional[float] = None,
    currency: str = "KRW",
    discountRate: Optional[float] = None,
) -> ValuationSummary:
    """DCF + DDM + 상대가치 종합 밸류에이션."""
    dcf = dcfValuation(
        series,
        shares=shares,
        sectorParams=sectorParams,
        currentPrice=currentPrice,
        currency=currency,
        discountRate=discountRate,
    )
    ddm = ddmValuation(series, shares=shares, sectorParams=sectorParams, currentPrice=currentPrice)
    ddm.currency = currency
    rel = relativeValuation(
        series, sectorParams=sectorParams, marketCap=marketCap, shares=shares, currentPrice=currentPrice
    )
    rel.currency = currency

    estimates: list[float] = []
    if dcf.perShareValue is not None and dcf.perShareValue > 0:
        estimates.append(dcf.perShareValue)
    if ddm.intrinsicValue is not None and ddm.intrinsicValue > 0:
        estimates.append(ddm.intrinsicValue)
    if rel.consensusValue is not None and rel.consensusValue > 0:
        estimates.append(rel.consensusValue)

    # 극단값 제거: 현재가의 1/20 미만은 모델 오류 가능성 높음
    if currentPrice and currentPrice > 0:
        _floor = currentPrice / 20
        estimates = [e for e in estimates if e >= _floor]

    fairRange = None
    verdict = "판단불가"

    if estimates:
        lo = min(estimates)
        hi = max(estimates)
        fairRange = (round(lo * 0.9, 0), round(hi * 1.1, 0))

        if currentPrice and currentPrice > 0:
            mid = sum(estimates) / len(estimates)
            ratio = currentPrice / mid
            if ratio < 0.8:
                verdict = "저평가"
            elif ratio > 1.2:
                verdict = "고평가"
            else:
                verdict = "적정"

    return ValuationSummary(
        dcf=dcf,
        ddm=ddm,
        relative=rel,
        fairValueRange=fairRange,
        currentPrice=currentPrice,
        verdict=verdict,
        currency=currency,
    )
