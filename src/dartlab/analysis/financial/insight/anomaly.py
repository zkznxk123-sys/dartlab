"""이상치 탐지 — 11개 룰 기반."""

from __future__ import annotations

import math

from dartlab.analysis.financial.insight.types import Anomaly, AuditDataForAnomaly
from dartlab.core.utils.extract import getAnnualValues


def _yoyChange(vals: list[float | None]) -> float | None:
    """최근 2개 유효값의 YoY 변화율 계산.

    Parameters
    ----------
    vals : list[float | None]
        연간 시계열 값 리스트.

    Returns
    -------
    float | None
        yoyPct : float | None — YoY 변화율 (%). 유효값 2개 미만이면 None.
    """
    from dartlab.analysis.financial.ratios import yoyPct

    valid = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(valid) < 2:
        return None
    _, prev = valid[-2]
    _, curr = valid[-1]
    return yoyPct(curr, prev)


def detectEarningsQuality(aSeries: dict, isFinancial: bool = False) -> list[Anomaly]:
    """이익 품질 이상치: 영업이익↑ but 영업CF↓ (금융업 제외).

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열 (IS/BS/CF 키 구조).
    isFinancial : bool
        금융업 여부. True이면 빈 리스트 반환.

    Returns
    -------
    list[Anomaly]
        severity : str — 'danger' | 'warning'
        category : str — 'earningsQuality'
        text : str — 이상치 설명 메시지
        magnitude : float — 괴리 크기 (%)
    """
    anomalies: list[Anomaly] = []

    if isFinancial:
        return anomalies

    opIncomeVals = getAnnualValues(aSeries, "IS", "operating_profit")
    opCfVals = getAnnualValues(aSeries, "CF", "operating_cashflow")

    opGrowth = _yoyChange(opIncomeVals)
    cfGrowth = _yoyChange(opCfVals)

    if opGrowth is not None and cfGrowth is not None:
        if opGrowth > 10 and cfGrowth < -10:
            anomalies.append(
                Anomaly(
                    "danger",
                    "earningsQuality",
                    f"이익↑(+{opGrowth:.0f}%) but 영업CF↓({cfGrowth:.0f}%) — 이익 품질 의심",
                    opGrowth - cfGrowth,
                )
            )
        elif opGrowth > 0 and cfGrowth < 0 and abs(cfGrowth) > 20:
            anomalies.append(
                Anomaly(
                    "warning",
                    "earningsQuality",
                    f"이익 증가(+{opGrowth:.0f}%) 대비 영업CF 감소({cfGrowth:.0f}%)",
                    opGrowth - cfGrowth,
                )
            )

    netIncomeVals = getAnnualValues(aSeries, "IS", "net_profit")

    latestNi = None
    latestCf = None
    for v in reversed(netIncomeVals):
        if v is not None:
            latestNi = v
            break
    for v in reversed(opCfVals):
        if v is not None:
            latestCf = v
            break

    if latestNi and latestCf and latestNi > 0 and latestCf < 0:
        anomalies.append(
            Anomaly(
                "danger",
                "earningsQuality",
                f"순이익 흑자({latestNi / 1e8:,.0f}억) but 영업CF 적자({latestCf / 1e8:,.0f}억)",
            )
        )

    return anomalies


def detectWorkingCapitalAnomaly(aSeries: dict) -> list[Anomaly]:
    """운전자본 이상치: 매출채권/재고 급증 > 매출 증가.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.

    Returns
    -------
    list[Anomaly]
        severity : str — 'warning' | 'info'
        category : str — 'workingCapital'
        text : str — 이상치 설명 메시지
        magnitude : float — 매출 대비 초과 증가율 (%p)
    """
    anomalies: list[Anomaly] = []

    arVals = getAnnualValues(aSeries, "BS", "trade_and_other_receivables")
    if not arVals:
        arVals = getAnnualValues(aSeries, "BS", "trade_and_other_receivables")
    invVals = getAnnualValues(aSeries, "BS", "inventories")
    revVals = getAnnualValues(aSeries, "IS", "sales")

    arGrowth = _yoyChange(arVals)
    invGrowth = _yoyChange(invVals)
    revGrowth = _yoyChange(revVals)

    if arGrowth is not None and revGrowth is not None:
        if arGrowth > revGrowth + 20 and arGrowth > 30:
            anomalies.append(
                Anomaly(
                    "warning",
                    "workingCapital",
                    f"매출채권 급증(+{arGrowth:.0f}%) > 매출 증가(+{revGrowth:.0f}%) — 수금 지연 가능",
                    arGrowth - revGrowth,
                )
            )

    if invGrowth is not None and revGrowth is not None:
        if invGrowth > revGrowth + 30 and invGrowth > 40:
            anomalies.append(
                Anomaly(
                    "warning",
                    "workingCapital",
                    f"재고자산 급증(+{invGrowth:.0f}%) > 매출 증가(+{revGrowth:.0f}%) — 재고 과잉 가능",
                    invGrowth - revGrowth,
                )
            )
    elif invGrowth is not None and invGrowth > 50:
        anomalies.append(
            Anomaly(
                "info",
                "workingCapital",
                f"재고자산 대폭 증가(+{invGrowth:.0f}%)",
                invGrowth,
            )
        )

    return anomalies


def detectBalanceSheetShift(aSeries: dict) -> list[Anomaly]:
    """BS 구조 급변: 부채/차입금/자본 ±50% 이상.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.

    Returns
    -------
    list[Anomaly]
        severity : str — 'danger' | 'warning' | 'info'
        category : str — 'balanceSheetShift'
        text : str — 항목별 급변 설명
        magnitude : float — YoY 변화율 (%)
    """
    anomalies: list[Anomaly] = []

    checkItems = [
        ("BS", "total_liabilities", "부채총계"),
        ("BS", "shortterm_borrowings", "단기차입금"),
        ("BS", "longterm_borrowings", "장기차입금"),
        ("BS", "debentures", "사채"),
        ("BS", "owners_of_parent_equity", "자본총계"),
    ]

    for sjDiv, snakeId, label in checkItems:
        vals = getAnnualValues(aSeries, sjDiv, snakeId)
        change = _yoyChange(vals)
        if change is not None and abs(change) > 50:
            direction = "급증" if change > 0 else "급감"
            severity = "warning" if abs(change) > 100 else "info"
            anomalies.append(
                Anomaly(
                    severity,
                    "balanceSheetShift",
                    f"{label} {direction} ({change:+.0f}%)",
                    change,
                )
            )

    equityVals = getAnnualValues(aSeries, "BS", "owners_of_parent_equity")
    valid = [v for v in equityVals if v is not None]
    if valid and valid[-1] is not None and valid[-1] < 0:
        anomalies.append(
            Anomaly(
                "danger",
                "balanceSheetShift",
                f"자본잠식 ({valid[-1] / 1e8:,.0f}억)",
                valid[-1],
            )
        )

    return anomalies


def detectCashBurn(aSeries: dict, isFinancial: bool = False) -> list[Anomaly]:
    """현금 소진: 현금 급감, 영업CF적자+재무CF양수 (금융업 제외).

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.
    isFinancial : bool
        금융업 여부. True이면 영업CF+재무CF 패턴 검사 스킵.

    Returns
    -------
    list[Anomaly]
        severity : str — 'warning'
        category : str — 'cashBurn'
        text : str — 현금 소진 설명
        magnitude : float — 현금 변화율 (%) 또는 None
    """
    anomalies: list[Anomaly] = []

    cashVals = getAnnualValues(aSeries, "BS", "cash_and_cash_equivalents")
    cashChange = _yoyChange(cashVals)

    if cashChange is not None and cashChange < -50:
        anomalies.append(
            Anomaly(
                "warning",
                "cashBurn",
                f"현금성 자산 급감 ({cashChange:.0f}%)",
                cashChange,
            )
        )

    opCfVals = getAnnualValues(aSeries, "CF", "operating_cashflow")
    finCfVals = getAnnualValues(aSeries, "CF", "cash_flows_from_financing_activities")

    latestOp = None
    latestFin = None
    for v in reversed(opCfVals):
        if v is not None:
            latestOp = v
            break
    for v in reversed(finCfVals):
        if v is not None:
            latestFin = v
            break

    if not isFinancial and latestOp is not None and latestOp < 0 and latestFin is not None and latestFin > 0:
        anomalies.append(
            Anomaly(
                "warning",
                "cashBurn",
                f"영업CF 적자({latestOp / 1e8:,.0f}억) + 재무CF 양수({latestFin / 1e8:,.0f}억) — 차입으로 영업적자 보전",
            )
        )

    return anomalies


def detectMarginDivergence(aSeries: dict) -> list[Anomaly]:
    """마진 급변: 영업이익률 ±5%p, 영업외손익 급변.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.

    Returns
    -------
    list[Anomaly]
        severity : str — 'info' | 'warning'
        category : str — 'marginDivergence'
        text : str — 마진 변동 설명
        magnitude : float — 마진 변동 (%p) 또는 영업외손익 비율 (%)
    """
    anomalies: list[Anomaly] = []

    revVals = getAnnualValues(aSeries, "IS", "sales")
    opVals = getAnnualValues(aSeries, "IS", "operating_profit")
    niVals = getAnnualValues(aSeries, "IS", "net_profit")

    validRev = [v for v in revVals if v is not None]
    validOp = [v for v in opVals if v is not None]
    validNi = [v for v in niVals if v is not None]

    if len(validRev) >= 2 and len(validOp) >= 2:
        prevMargin = (validOp[-2] / validRev[-2] * 100) if validRev[-2] and validRev[-2] != 0 else None
        currMargin = (validOp[-1] / validRev[-1] * 100) if validRev[-1] and validRev[-1] != 0 else None

        if prevMargin is not None and currMargin is not None:
            marginShift = currMargin - prevMargin
            if abs(marginShift) > 5:
                direction = "개선" if marginShift > 0 else "악화"
                severity = "info" if marginShift > 0 else "warning"
                anomalies.append(
                    Anomaly(
                        severity,
                        "marginDivergence",
                        f"영업이익률 {direction} ({prevMargin:.1f}% → {currMargin:.1f}%, {marginShift:+.1f}%p)",
                        marginShift,
                    )
                )

    if len(validOp) >= 2 and len(validNi) >= 2:
        prevGap = validNi[-2] - validOp[-2] if validOp[-2] is not None and validNi[-2] is not None else None
        currGap = validNi[-1] - validOp[-1] if validOp[-1] is not None and validNi[-1] is not None else None

        if prevGap is not None and currGap is not None:
            gapChange = currGap - prevGap
            if abs(gapChange) > 0 and validOp[-1] and validOp[-1] != 0:
                gapRatio = (abs(gapChange) / abs(validOp[-1])) * 100
                if gapRatio > 30:
                    anomalies.append(
                        Anomaly(
                            "warning",
                            "marginDivergence",
                            f"영업외손익 급변 (영업이익 대비 {gapRatio:.0f}% 규모 변동)",
                            gapRatio,
                        )
                    )

    return anomalies


def detectFinancialSectorAnomaly(aSeries: dict, isFinancial: bool) -> list[Anomaly]:
    """금융업 전용 이상치: 부채비율 급변, 순이익 급감.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열.
    isFinancial : bool
        금융업 여부. False이면 빈 리스트 반환.

    Returns
    -------
    list[Anomaly]
        severity : str — 'warning'
        category : str — 'financialSector'
        text : str — 금융업 이상치 설명
        magnitude : float — 부채비율 변동 (%p) 또는 순이익 변화율 (%)
    """
    if not isFinancial:
        return []

    anomalies: list[Anomaly] = []

    liabVals = getAnnualValues(aSeries, "BS", "total_liabilities")
    equityVals = getAnnualValues(aSeries, "BS", "owners_of_parent_equity") or getAnnualValues(
        aSeries, "BS", "total_stockholders_equity"
    )

    validLiab = [v for v in liabVals if v is not None]
    validEq = [v for v in equityVals if v is not None]

    if len(validLiab) >= 2 and len(validEq) >= 2:
        prevDr = (validLiab[-2] / validEq[-2] * 100) if validEq[-2] and validEq[-2] > 0 else None
        currDr = (validLiab[-1] / validEq[-1] * 100) if validEq[-1] and validEq[-1] > 0 else None

        if prevDr is not None and currDr is not None:
            drShift = currDr - prevDr
            if abs(drShift) > 100:
                direction = "급증" if drShift > 0 else "급감"
                anomalies.append(
                    Anomaly(
                        "warning",
                        "financialSector",
                        f"금융업 부채비율 {direction} ({prevDr:.0f}% → {currDr:.0f}%, {drShift:+.0f}%p)",
                        drShift,
                    )
                )

    niVals = getAnnualValues(aSeries, "IS", "net_profit")
    niChange = _yoyChange(niVals)
    if niChange is not None and niChange < -30:
        anomalies.append(
            Anomaly(
                "warning",
                "financialSector",
                f"금융업 순이익 급감 ({niChange:.0f}%)",
                niChange,
            )
        )

    return anomalies


# ── Trend/CCC/Audit/Benford/RevenueQuality detector + _isBig4 → _anomalyDeep.py 분리 ──

from dartlab.analysis.financial.insight._anomalyDeep import (  # noqa: E402
    _isBig4,
    detectAuditRedFlags,
    detectBenfordAnomaly,
    detectCCCDeterioration,
    detectRevenueQuality,
    detectTrendDeterioration,
)


def runAnomalyDetection(
    aSeries: dict,
    isFinancial: bool = False,
    *,
    auditData: AuditDataForAnomaly | None = None,
) -> list[Anomaly]:
    """전체 이상치 탐지 실행 — 11개 룰 기반 종합.

    Parameters
    ----------
    aSeries : dict
        연간 재무 시계열 (IS/BS/CF 키 구조).
    isFinancial : bool
        금융업 여부.
    auditData : AuditDataForAnomaly | None
        감사 데이터. None이면 감사 탐지기 스킵 (하위호환).

    Returns
    -------
    list[Anomaly]
        severity 기준 정렬된 이상치 리스트.
        severity : str — 'danger' > 'warning' > 'info' 순
        category : str — 이상치 분류 (earningsQuality, workingCapital, balanceSheetShift 등)
        text : str — 한국어 이상치 설명
        magnitude : float | None — 이상치 크기
    """
    anomalies: list[Anomaly] = []
    anomalies.extend(detectEarningsQuality(aSeries, isFinancial))
    anomalies.extend(detectWorkingCapitalAnomaly(aSeries))
    anomalies.extend(detectBalanceSheetShift(aSeries))
    anomalies.extend(detectCashBurn(aSeries, isFinancial))
    anomalies.extend(detectMarginDivergence(aSeries))
    anomalies.extend(detectFinancialSectorAnomaly(aSeries, isFinancial))
    anomalies.extend(detectTrendDeterioration(aSeries, isFinancial))
    anomalies.extend(detectCCCDeterioration(aSeries, isFinancial))
    # 세계적 감사 기법 — Phase 086
    anomalies.extend(detectAuditRedFlags(auditData))
    anomalies.extend(detectBenfordAnomaly(aSeries))
    anomalies.extend(detectRevenueQuality(aSeries))

    anomalies.sort(key=lambda a: {"danger": 0, "warning": 1, "info": 2}.get(a.severity, 3))
    return anomalies
