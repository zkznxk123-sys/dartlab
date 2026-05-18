"""capital.py 의 유동성 — Liquidity + 보조 헬퍼."""

from __future__ import annotations

from dartlab.analysis.financial._capitalStructure import (
    _calcImpliedBorrowingRate,
    _calcNetDebtEbitda,
    _fmtAmt,
    _getRatios,
    _latestAnnualVal,
    _quarterlyCols,
)
from dartlab.analysis.financial.accountSums import sumBorrowings
from dartlab.core.memory import memoizedCalc
from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

_MAX_QUARTERS = 5
_MAX_YEARS = 8


@memoizedCalc
def calcLiquidity(company, *, basePeriod: str | None = None) -> dict | None:
    """유동성 4 지표 (유동비율 + 당좌비율 + 현금비율 + 순운전자본) 정성 평가 라벨.

    Capabilities:
        ratios 의 4 유동성 지표 + 순운전자본 (WC) 을 한국어 정성 라벨 (안정/
        보통/주의) 함께 산출. analysis() 의 안정성 축 표시용. credit
        engine 의 metrics 와 별도 (간단 표시 목적).

    Args:
        company: Company 객체.
        basePeriod: 기준 기간. None 시 최신.

    Returns:
        dict | None:
            - ``metrics`` (list[tuple[str, str]]): ("유동비율", "150% — 안정")
              형식. ratios=None 시 None.

    Raises:
        없음.

    Example:
        >>> r = calcLiquidity(Company("005930"))
        >>> r["metrics"][0]
        ('유동비율', '180% — 안정')

    Guide:
        임계값: 유동비율 ≥ 150% = 안정, 100~150% = 보통, < 100% = 주의.
        당좌비율 ≥ 100% = 즉시 동원 가능. 본 함수는 credit engine 의 7 축
        분해와 별도 — 사용자 보고용 간단 표시.

    When:
        analysis() 안정성 축 표시 또는 사용자 보고서에서 유동성 지표를 정성
        라벨과 함께 보여줄 때.

    How:
        ``_getRatios`` 로 ratios 스냅샷을 얻고 4 지표를 정성 임계값에 매칭한
        metrics tuple list 로 변환.

    SeeAlso:
        - ``credit.scoring.metrics.calcAllMetrics``: 7 축 정량 지표
        - ``narrateLiquidity``: credit 의 유동성 서사 생성
        - ``calcCashFlowStructure``: 현금흐름 구조 (보완)

    Requires:
        Company.finance (BS) + ratios 헬퍼.

    AIContext:
        라벨 "주의" 결과 단독 인용 금지 — 단기차입금 비중 + 현금 흐름 함께
        확인. KR 대기업은 차환 의존 (CR>150 + STDR>50) 흔하므로 모순 진단
        필요.

    LLM Specifications:
        AntiPatterns:
            - 유동비율 200%+ 회사 → "유동성 매우 우수" 단정 — 현금 보유 과다
              가능 (배당/투자 부진 신호). cashRatio 함께 확인.
            - ratios=None 시 None 반환 — 호출자 분기 필요.
        OutputSchema:
            ``{metrics: list[tuple[str, str]]}`` 또는 None.
        Prerequisites:
            BS 시계열 + _getRatios 헬퍼 로드.
        Freshness:
            BS 최신 분기.
        Dataflow:
            company → _getRatios → currentRatio/quickRatio/cashRatio + WC →
            한국어 라벨 → metrics list.
        TargetMarkets: KR (DART), US (EDGAR — 동일 비율 표준).
    """
    ratios = _getRatios(company)
    if ratios is None:
        return None

    metrics = []

    cr = getattr(ratios, "currentRatio", None)
    if cr is not None:
        quality = "안정" if cr >= 150 else "보통" if cr >= 100 else "주의"
        metrics.append(("유동비율", f"{cr:.0f}% — {quality}"))

    qr = getattr(ratios, "quickRatio", None)
    if qr is not None:
        metrics.append(("당좌비율", f"{qr:.0f}%"))

    car = getattr(ratios, "cashRatio", None)
    if car is not None:
        metrics.append(("현금비율", f"{car:.0f}%"))

    wc = getattr(ratios, "workingCapital", None)
    if wc is not None:
        metrics.append(("순운전자본", _fmtAmt(wc)))

    if not metrics:
        return None

    return {"metrics": metrics}


# ── calcCashFlowStructure + calcDistressIndicators + _sign/_classifyCfPattern/_isFinancialCompany → _capitalCashflow.py 분리 ──

from dartlab.analysis.financial._capitalCashflow import (  # noqa: E402, F401
    _classifyCfPattern,
    _isFinancialCompany,
    _sign,
    calcCashFlowStructure,
    calcDistressIndicators,
)

# ── 내부 헬퍼 ──


def _calcRetainedPct(equityRow, retainedRow) -> float | None:
    """이익잉여금 / 자본총계 비중.

    Returns
    -------
    float | None
        내부유보 비중 (%). 데이터 없으면 None.
    """
    if equityRow is None or retainedRow is None:
        return None
    for key in equityRow:
        eq = equityRow.get(key)
        re = retainedRow.get(key)
        if eq and re and eq != 0:
            return re / eq * 100
    return None


def _calcFinDebtPct(liabRow, stbRow, ltbRow, bondRow) -> float | None:
    """금융부채 / 부채총계 비중 — 최신 기간.

    Returns
    -------
    float | None
        금융부채 비중 (%). 데이터 없으면 None.
    """
    if liabRow is None:
        return None
    for key in liabRow:
        tl = liabRow.get(key)
        if tl is None or tl == 0:
            continue
        stb = (stbRow or {}).get(key)
        ltb = (ltbRow or {}).get(key)
        bond = (bondRow or {}).get(key)
        parts = [v for v in [stb, ltb, bond] if v is not None]
        if parts:
            return sum(parts) / tl * 100
    return None


# 분리된 함수 (BC re-export)
from dartlab.analysis.financial._capitalFunding import (  # noqa: E402, F401
    calcCapitalFlags,
    calcFundingSources,
)
