"""Normalized Earnings — Damodaran Investment Valuation Ch.22.

사이클/회복 기업의 dFV 오탐 해결 (예: 한국전력 적자→흑자 전환 기준 DCF 과대).

핵심 아이디어 (Damodaran 권고):
- 사이클 바닥이나 회복 초기 기준 FCF 중앙값은 업사이클 평균을 반영하지 못함
- 양수 마진만 5~10년 lookback 중앙값으로 Normalized OI 계산
- 재투자율 빼고 tax shield 후 Normalized FCF 산출

조건부 적용 (분기 규약):
- lifeCyclePhase in {decline, turnaround} 또는 최근 5Y ROIC 중 적자 1회 이상
- 그 외 (matureGrowth/matureStable/highGrowth) 는 기존 FCF 중앙값 유지
"""

from __future__ import annotations

from statistics import median


def calcNormalizedFcf(
    revenueHistory: list[float] | None,
    marginHistory: list[float] | None,
    *,
    lookbackYears: int = 5,
    taxRate: float = 0.22,
    reinvestmentRate: float = 0.35,
) -> dict:
    """Damodaran Ch.22 — 사이클/회복 기업 정규화 FCF.

    공식:
        Normalized Margin = 양수 마진 중앙값 (사이클 중립화)
        Normalized OI = latest Revenue × Normalized Margin
        Normalized FCF = Normalized OI × (1 - tax) × (1 - reinvestmentRate)

    Capabilities:
        - 사이클/회복 기업의 정상 마진·OI·FCF 산출.

    Guide:
        양수 마진 중앙값으로 사이클 평탄화 → latest revenue 곱.

    When:
        decline/turnaround 기업 DCF 입력 정상화가 필요할 때.

    How:
        margin 중앙값 → NOPAT = OI×(1-tax) → FCF = NOPAT×(1-reinvest).

    Requires:
        revenue/margin history ≥ 3 점.

    Raises:
        없음 (skip dict 반환).

    Example:
        >>> calcNormalizedFcf([100,90,110], [0.05,-0.02,0.06])["method"]
        "median_positive_margin"

    See Also:
        - needsNormalized : 적용 조건 판단
        - calcLifeCycle : phase 라벨

    AIContext:
        AI 가 적자 이력 기업 DCF 답변에 "정규화 FCF" 인용 시 사용.

    Parameters
    ----------
    revenueHistory : 매출 시계열 (최신 먼저 권장, 하지만 자동 정렬 안 함 — 입력 그대로)
    marginHistory : 영업마진 시계열 (소수 0.0~1.0). revenue 와 같은 인덱스 순서
    lookbackYears : 과거 몇 년까지 볼지 (기본 5)
    taxRate : 실효세율 (기본 22%)
    reinvestmentRate : 재투자율 (기본 35% — mature 평균)

    Returns
    -------
    dict
        normalizedMargin : float — 양수 중앙값 (0.0~1.0). skip 시 None
        normalizedOI : float — latest rev × normalized margin. skip 시 None
        normalizedFcf : float — NOPAT × (1-reinvest). skip 시 None
        method : "median_positive_margin" | "mean_all_margin" | "skip"
        sampleYears : int — 실제 사용한 샘플 수
        warnings : list[str]
    """
    warnings: list[str] = []

    if not revenueHistory or not marginHistory:
        return _skipResult("revenue or margin history empty")

    # lookback 제한
    revs = list(revenueHistory)[:lookbackYears]
    margins = list(marginHistory)[:lookbackYears]

    if len(revs) < 3 or len(margins) < 3:
        return _skipResult(f"sample < 3 (revs={len(revs)}, margins={len(margins)})")

    # 최신 revenue (첫 인덱스)
    latest_rev: float | None = None
    for r in revs:
        if isinstance(r, (int, float)) and r > 0:
            latest_rev = float(r)
            break
    if latest_rev is None:
        return _skipResult("no positive revenue")

    # 양수 마진 중앙값 (사이클 중립화)
    positive_margins = [float(m) for m in margins if isinstance(m, (int, float)) and m > 0]

    if len(positive_margins) >= 2:
        normalized_margin = median(positive_margins)
        method = "median_positive_margin"
        sample = len(positive_margins)
    else:
        # 양수 샘플 부족 → 전체 평균 (음수 포함), 대신 경고
        valid_margins = [float(m) for m in margins if isinstance(m, (int, float))]
        if not valid_margins:
            return _skipResult("no valid margin data")
        normalized_margin = sum(valid_margins) / len(valid_margins)
        method = "mean_all_margin"
        sample = len(valid_margins)
        warnings.append("양수 마진 < 2 — 전체 평균 사용 (정확도 낮음)")

    # 음수 정규화 margin 은 skip (구조적 적자 기업 — 청산/decline 로 가야지 DCF 부적절)
    if normalized_margin <= 0:
        return _skipResult(f"normalized margin {normalized_margin:.3f} ≤ 0")

    # sanity: 극단 margin cap (0.5 = 50%)
    if normalized_margin > 0.5:
        warnings.append(f"normalized margin {normalized_margin:.2%} 이상치 — 0.5 cap 적용")
        normalized_margin = 0.5

    # Normalized OI + FCF
    tax = max(0.0, min(0.5, float(taxRate)))
    reinvest = max(0.0, min(0.8, float(reinvestmentRate)))

    normalized_oi = latest_rev * normalized_margin
    normalized_fcf = normalized_oi * (1.0 - tax) * (1.0 - reinvest)

    return {
        "normalizedMargin": round(normalized_margin, 4),
        "normalizedOI": round(normalized_oi, 0),
        "normalizedFcf": round(normalized_fcf, 0),
        "method": method,
        "sampleYears": sample,
        "warnings": warnings,
    }


def needsNormalized(
    lifeCyclePhase: str | None,
    roicHistory: list[dict] | None,
    *,
    lookbackYears: int = 5,
) -> bool:
    """Normalized Earnings 적용 필요 여부 판단.

    조건 (둘 중 하나):
    1. lifeCyclePhase in {decline, turnaround}
    2. 최근 lookbackYears 내 ROIC 음수 1회 이상 (가치 파괴 이력)

    건강한 기업 (matureGrowth/matureStable/highGrowth 중 ROIC 지속 양수) 은 False.

    Capabilities:
        - 정규화 FCF 적용 필요/불필요 boolean 게이트.

    Guide:
        라이프사이클 + ROIC 이력 두 신호로 게이트.

    When:
        DCF 입력값 정규화할지 라우팅 결정 직전.

    How:
        phase ∈ {decline, turnaround} 또는 최근 ROIC 음수 1회+ → True.

    Requires:
        lifeCyclePhase 또는 roicHistory 중 하나.

    Raises:
        없음 (None 입력 시 False).

    Example:
        >>> needsNormalized("decline", None)
        True

    See Also:
        - calcNormalizedFcf : 본 게이트 통과 시 호출
        - calcLifeCycle : phase 산출

    AIContext:
        AI 가 valuation pipeline 라우팅 시 normalized branch 선택에 사용.
    """
    if lifeCyclePhase in ("decline", "turnaround"):
        return True

    if not roicHistory:
        return False

    for h in list(roicHistory)[:lookbackYears]:
        if not isinstance(h, dict):
            continue
        roic = h.get("roic")
        if isinstance(roic, (int, float)) and roic < 0:
            return True

    return False


def _skipResult(reason: str) -> dict:
    """계산 불가 시 skip 표시."""
    return {
        "normalizedMargin": None,
        "normalizedOI": None,
        "normalizedFcf": None,
        "method": "skip",
        "sampleYears": 0,
        "warnings": [reason],
    }
