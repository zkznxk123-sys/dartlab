"""부실 예측 종합 스코어카드.

5축 가중 평균으로 기업 부실 위험을 종합 판정한다.
실험 084_distressModels Phase 1-4 + 085_mertonEngine 검증 결과 기반.

축 구성 (100점 만점, 0=안전 100=위험):
- 정량 분석 (30%): O-Score, Z''-Score, Z-Score  [Merton 없으면 40%]
- 시장 기반 (20%): Merton D2D + PD              [Merton 없으면 0%]
- 이익 품질 (15%): Beneish M-Score, Sloan Accrual, Piotroski F-Score  [없으면 20%]
- 추세 분석 (25%): anomaly에서 탐지된 시계열 패턴  [없으면 30%]
- 감사 위험 (10%): 감사의견 비적정 등

Merton 미제공 시 기존 4축(40/20/30/10) 그대로 동작 (하위호환 100%).
금융업(isFinancial=True) → Merton 무시 (은행 부채 구조적 왜곡).

레벨: safe(<15), watch(<30), warning(<50), danger(<70), critical(>=70)
신용등급: AAA~D (S&P PD 매핑)
"""

from __future__ import annotations

from dartlab.analysis.financial.insight.types import (
    Anomaly,
    DistressAxis,
    DistressResult,
    ModelScore,
)
from dartlab.analysis.financial.ratios import RatioResult

# Merton D2D 입력은 dict 로 받는다 (credit 도메인의 MertonResult dataclass 직접 import 회피).
# 호출자 (Company facade · review) 가 credit.calcMerton() 결과를 dict 로 변환해 전달.
# dict 키: d2d (float), pd (float), converged (bool).

# ── 신용등급 매핑 테이블 (S&P PD↔Rating 대응) ──

_CREDIT_GRADE_TABLE: list[tuple[float, str, str]] = [
    (5, "AAA", "투자적격 최상위"),
    (10, "AA", "투자적격 상위"),
    (15, "A", "투자적격"),
    (25, "BBB", "투자적격 하한"),
    (35, "BB", "투기등급"),
    (50, "B", "투기등급 하위"),
    (65, "CCC", "상당한 부실 위험"),
    (80, "CC", "부실 임박"),
    (90, "C", "부도 직전"),
    (100, "D", "부도 수준"),
]


def _mapCreditGrade(overall: float) -> tuple[str, str]:
    """종합 점수 → (등급, 설명). 기존 10단계.

    Parameters
    ----------
    overall : float
        종합 부실 점수 (0~100) (점).

    Returns
    -------
    tuple[str, str]
        grade : str — 신용등급 ('AAA'~'D')
        description : str — 등급 설명
    """
    for threshold, grade, desc in _CREDIT_GRADE_TABLE:
        if overall < threshold:
            return grade, desc
    return "D", "부도 수준"


def _mapCreditGrade20(overall: float) -> tuple[str, str, float]:
    """종합 점수 → (등급, 설명, PD%). 20단계 세분화.

    Parameters
    ----------
    overall : float
        종합 부실 점수 (0~100) (점).

    Returns
    -------
    tuple[str, str, float]
        grade : str — 20단계 세분화 신용등급
        description : str — 등급 설명
        pd : float — 부도 확률 (%)
    """
    from dartlab.synth.creditGradeTable import mapTo20Grade

    return mapTo20Grade(overall)


# ── 개별 모델 해석/정규화 함수 → _distressModels.py 분리 ──

from dartlab.analysis.financial.insight._distressModels import (  # noqa: E402
    _interpretAltmanZ,
    _interpretAltmanZpp,
    _interpretAuditRedFlags,
    _interpretBeneish,
    _interpretMerton,
    _interpretOhlson,
    _interpretPiotroski,
    _interpretSloan,
    _normalizeBeneish,
    _normalizeFScore,
    _normalizeMerton,
    _normalizeOhlson,
    _normalizeSloan,
    _normalizeZ,
    _normalizeZpp,
)

# ── 유동성 경보 ──


def _calcCashRunway(ratios: RatioResult) -> tuple[float | None, str | None]:
    """현금 소진 예상 개월 수 계산.

    Parameters
    ----------
    ratios : RatioResult
        재무비율 계산 결과.

    Returns
    -------
    tuple[float | None, str | None]
        months : float | None — 현금 소진 예상 개월 수 (개월). 산정 불가 시 None.
        alert : str | None — 유동성 경보 수준 ('충분'~'위험').
    """
    cash = ratios.cash or 0
    ocf = ratios.operatingCashflowTTM

    if ocf is not None and ocf > 0:
        return 999, "충분 (영업CF 양수, 현금 축적 중)"

    cogs = ratios.costOfSales or 0
    sga = ratios.sga or 0
    monthly_opex = (cogs + sga) / 12 if (cogs + sga) > 0 else None

    if monthly_opex is None or monthly_opex <= 0:
        return None, None

    monthly_burn = abs(ocf / 12) if ocf else monthly_opex
    if monthly_burn <= 0:
        return None, None

    months = cash / monthly_burn

    if months > 24:
        alert = "충분 (2년+)"
    elif months > 12:
        alert = "양호 (1~2년)"
    elif months > 6:
        alert = "주의 (6~12개월)"
    elif months > 3:
        alert = "경고 (3~6개월)"
    else:
        alert = "위험 (3개월 미만)"

    return round(months, 1), alert


# ── 위험 요인 추출 ──


def _extractRiskFactors(
    anomalies: list[Anomaly],
    ratios: RatioResult,
) -> list[str]:
    """anomaly + ratios에서 구조화된 위험 요인 목록 추출.

    Parameters
    ----------
    anomalies : list[Anomaly]
        이상치 탐지 결과.
    ratios : RatioResult
        재무비율 계산 결과.

    Returns
    -------
    list[str]
        위험 요인 텍스트 목록.
    """
    factors: list[str] = []

    for a in anomalies:
        if a.severity in ("danger", "warning"):
            factors.append(a.text)

    if ratios.ohlsonProbability is not None and ratios.ohlsonProbability > 10:
        factors.append(f"O-Score 부도 확률 {ratios.ohlsonProbability:.1f}%")

    if ratios.altmanZppScore is not None and ratios.altmanZppScore < 1.1:
        factors.append(f"Z''-Score {ratios.altmanZppScore:.2f} (부실 영역)")

    if ratios.beneishMScore is not None and ratios.beneishMScore > -2.22:
        factors.append(f"Beneish M-Score {ratios.beneishMScore:.2f} (이익 조작 의심)")

    if ratios.piotroskiFScore is not None and ratios.piotroskiFScore <= 2:
        factors.append(f"Piotroski F-Score {ratios.piotroskiFScore}/9 (펀더멘탈 심각)")

    return factors


# ── 데이터 품질 판정 ──


def _assessDataQuality(modelCount: int) -> str:
    """모델 수 기반 데이터 품질 판정.

    Parameters
    ----------
    modelCount : int
        사용된 모델 수.

    Returns
    -------
    str
        quality : str — '충분' (>=5) | '보통' (>=3) | '부족'
    """
    if modelCount >= 5:
        return "충분"
    if modelCount >= 3:
        return "보통"
    return "부족"


# ── 메인 함수 ──


def calcDistress(
    ratios: RatioResult,
    anomalies: list[Anomaly],
    isFinancial: bool = False,
    *,
    mertonResult: dict | None = None,
) -> DistressResult:
    """부실 예측 종합 스코어카드 계산.

    각 모델의 원시 값 → zone 판정 → 해석 텍스트 → 학술 참조를 포함한
    세계 수준의 근거 기반 레포트를 생성한다.

    mertonResult가 제공되면 5축(30/20/15/25/10), 미제공 시 4축(40/20/30/10).
    isFinancial=True이면 Merton을 무시한다 (은행 부채 구조적 왜곡).

    Parameters
    ----------
    ratios : RatioResult
        재무비율 결과.
    anomalies : list[Anomaly]
        감지된 이상 신호 목록.
    isFinancial : bool
        금융업 여부.
    mertonResult : dict | None
        Merton D2D 결과 dict (``{"d2d": float, "pd": float, "converged": bool}``).
        호출자가 ``credit.calcMerton()`` 결과를 dict 변환해 전달.

    Returns
    -------
    DistressResult
        종합 부실 점수, zone, 개별 모델 판정, 해석 텍스트.
    """
    # Merton 사용 여부: 비금융 + 수렴된 결과만
    useMerton = mertonResult is not None and not isFinancial and mertonResult.get("converged", False)

    # ── 1. 정량 축 ──
    quant_models: list[ModelScore] = []
    quant_norms: list[float] = []

    if ratios.ohlsonProbability is not None:
        quant_models.append(_interpretOhlson(ratios.ohlsonProbability))
        quant_norms.append(_normalizeOhlson(ratios.ohlsonProbability))

    if ratios.altmanZppScore is not None:
        quant_models.append(_interpretAltmanZpp(ratios.altmanZppScore))
        quant_norms.append(_normalizeZpp(ratios.altmanZppScore))

    if ratios.altmanZScore is not None:
        quant_models.append(_interpretAltmanZ(ratios.altmanZScore))
        quant_norms.append(_normalizeZ(ratios.altmanZScore))

    quant_score = sum(quant_norms) / len(quant_norms) if quant_norms else 0
    quant_zones = [m.zone for m in quant_models]
    if not quant_models:
        quant_summary = "정량 모델 데이터 부족."
    elif all(z == "safe" for z in quant_zones):
        quant_summary = f"{len(quant_models)}개 모델 모두 안전 영역."
    elif any(z == "distress" for z in quant_zones):
        n_distress = sum(1 for z in quant_zones if z == "distress")
        quant_summary = f"{n_distress}/{len(quant_models)}개 모델 부실 영역. 즉각 점검 필요."
    else:
        quant_summary = f"{len(quant_models)}개 모델 회색 영역 포함. 모니터링 권고."

    quant_axis = DistressAxis(
        name="정량 분석",
        score=round(quant_score, 1),
        weight=0.30 if useMerton else 0.40,
        models=quant_models,
        summary=quant_summary,
    )

    # ── 2. 이익 품질 축 ──
    eq_models: list[ModelScore] = []
    eq_norms: list[float] = []

    if ratios.beneishMScore is not None:
        eq_models.append(_interpretBeneish(ratios.beneishMScore))
        eq_norms.append(_normalizeBeneish(ratios.beneishMScore))

    if ratios.sloanAccrualRatio is not None:
        eq_models.append(_interpretSloan(ratios.sloanAccrualRatio))
        eq_norms.append(_normalizeSloan(ratios.sloanAccrualRatio))

    if ratios.piotroskiFScore is not None:
        eq_models.append(_interpretPiotroski(ratios.piotroskiFScore))
        eq_norms.append(_normalizeFScore(ratios.piotroskiFScore))

    eq_score = sum(eq_norms) / len(eq_norms) if eq_norms else 0
    if not eq_models:
        eq_summary = "이익 품질 모델 데이터 부족."
    elif all(m.zone == "safe" for m in eq_models):
        eq_summary = f"{len(eq_models)}개 지표 모두 양호. 이익 품질 건전."
    elif any(m.zone == "distress" for m in eq_models):
        eq_summary = "이익 품질 의심 지표 존재. 회계 검토 권고."
    else:
        eq_summary = "이익 품질 보통. 일부 지표 모니터링 필요."

    eq_axis = DistressAxis(
        name="이익 품질",
        score=round(eq_score, 1),
        weight=0.15 if useMerton else 0.20,
        models=eq_models,
        summary=eq_summary,
    )

    # ── 3. 추세 축 ──
    trend_score = 0.0
    trend_anomalies = [a for a in anomalies if a.category in ("trendDeterioration", "cccDeterioration")]
    for a in trend_anomalies:
        if a.severity == "danger":
            trend_score += 40
        elif a.severity == "warning":
            trend_score += 25
        else:
            trend_score += 10
    trend_score = min(trend_score, 100)

    if not trend_anomalies:
        trend_summary = "시계열 악화 패턴 없음."
    else:
        n_danger = sum(1 for a in trend_anomalies if a.severity == "danger")
        trend_summary = f"악화 패턴 {len(trend_anomalies)}건 탐지"
        if n_danger:
            trend_summary += f" (심각 {n_danger}건). 즉각 점검 필요."
        else:
            trend_summary += ". 모니터링 권고."

    trend_axis = DistressAxis(
        name="추세 분석",
        score=round(trend_score, 1),
        weight=0.25 if useMerton else 0.30,
        summary=trend_summary,
    )

    # ── 4. 감사 축 ──
    audit_score = 0.0
    audit_anomalies = [a for a in anomalies if a.category in ("audit", "governance")]
    audit_models: list[ModelScore] = []

    # 감사 Red Flag 수 기반 점수
    n_critical = sum(1 for a in audit_anomalies if a.severity == "danger")
    n_total = len(audit_anomalies)

    if n_total > 0:
        audit_models.append(_interpretAuditRedFlags(n_total, n_critical > 0))

    for a in audit_anomalies:
        if a.severity == "danger":
            audit_score += 50
        elif a.severity == "warning":
            audit_score += 25
    audit_score = min(audit_score, 100)

    if not audit_anomalies:
        audit_summary = "감사 이상징후 없음."
    elif n_critical > 0:
        audit_summary = f"감사 Red Flag {n_total}건 (심각 {n_critical}건). 즉각 점검 필요."
    else:
        audit_summary = f"감사 이상 {n_total}건 탐지. 모니터링 권고."

    audit_axis = DistressAxis(
        name="감사 위험",
        score=round(audit_score, 1),
        weight=0.10,
        models=audit_models,
        summary=audit_summary,
    )

    # ── 5. 시장 기반 축 (Merton) ──
    axes = [quant_axis]

    if useMerton:
        assert mertonResult is not None  # type narrowing
        merton_model = _interpretMerton(mertonResult)
        merton_d2d = mertonResult["d2d"]
        merton_norm = _normalizeMerton(merton_d2d)
        merton_score = merton_norm

        if merton_d2d > 4:
            merton_summary = f"D2D {merton_d2d:.2f} — 시장 기반 부도 거리 충분."
        elif merton_d2d > 2:
            merton_summary = f"D2D {merton_d2d:.2f} — 모니터링 필요."
        elif merton_d2d > 1:
            merton_summary = f"D2D {merton_d2d:.2f} — 부실 위험 영역."
        else:
            merton_summary = f"D2D {merton_d2d:.2f} — 부도 임박 영역."

        market_axis = DistressAxis(
            name="시장 기반",
            score=round(merton_score, 1),
            weight=0.20,
            models=[merton_model],
            summary=merton_summary,
        )
        axes.append(market_axis)

    axes.extend([eq_axis, trend_axis, audit_axis])

    # ── 종합 ──
    overall = sum(ax.score * ax.weight for ax in axes)

    if overall >= 70:
        level = "critical"
    elif overall >= 50:
        level = "danger"
    elif overall >= 30:
        level = "warning"
    elif overall >= 15:
        level = "watch"
    else:
        level = "safe"

    creditGrade, creditDesc = _mapCreditGrade(overall)

    # 유동성
    cashMonths, liquidityAlert = _calcCashRunway(ratios)

    # 위험 요인
    riskFactors = _extractRiskFactors(anomalies, ratios)
    if useMerton and mertonResult is not None and mertonResult["d2d"] < 2.0:
        riskFactors.append(f"Merton D2D {mertonResult['d2d']:.2f} (부실 영역, PD={mertonResult['pd']:.1f}%)")

    # 모델 수 / 데이터 품질
    modelCount = len(quant_models) + len(eq_models) + (1 if useMerton else 0)
    dataQuality = _assessDataQuality(modelCount)

    return DistressResult(
        level=level,
        overall=round(overall, 1),
        creditGrade=creditGrade,
        creditDescription=creditDesc,
        axes=axes,
        cashRunwayMonths=cashMonths,
        liquidityAlert=liquidityAlert,
        riskFactors=riskFactors,
        modelCount=modelCount,
        dataQuality=dataQuality,
    )
