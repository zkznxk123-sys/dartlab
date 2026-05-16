"""Merton 구조 모형 — Distance to Default (D2D) + 부도 확률 (PD).

Merton (1974) 모형을 2-방정식 Newton-Raphson으로 풀어
주가 변동성 + 부채에서 부도 거리와 부도 확률을 추정한다.

Moody's KMV가 전 세계 은행에서 사용하는 사실상 표준.

수학:
    기업 자산 V는 GBM을 따른다고 가정.
    주식 E = V·N(d₁) - D·e^(-rT)·N(d₂)  (Black-Scholes call)
    σ_E·E = V·N(d₁)·σ_A                   (Itô 보조정리)
    D2D = (ln(V/D) + (r - σ_A²/2)·T) / (σ_A·√T)
    PD = N(-D2D) × 100  (%)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_SQRT2 = math.sqrt(2.0)
_INV_SQRT2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _normCdf(x: float) -> float:
    """표준 정규 CDF — math.erf 기반 (scipy 불필요)."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _normPdf(x: float) -> float:
    """표준 정규 PDF."""
    return _INV_SQRT2PI * math.exp(-0.5 * x * x)


@dataclass(slots=True)
class MertonResult:
    """Merton 모형 풀이 결과."""

    assetValue: float  # V₀ (추정 자산가치)
    assetVolatility: float  # σ_A (비율, 0.25 = 25%)
    d2d: float  # Distance to Default
    pd: float  # 부도확률 (%)
    equityValue: float  # E (시가총액)
    debtFaceValue: float  # D (총부채)
    riskFreeRate: float  # r
    maturity: float  # T
    equityVolatility: float  # σ_E (비율)
    converged: bool
    iterations: int


def calcEquityVolatility(returns: list[float], tradingDays: int = 252) -> float:
    """일별 수익률 시계열 → 연환산 주식 변동성 σ_E.

    Capabilities:
        일별 수익률 리스트의 sample std (ddof=1) 를 ``√tradingDays`` 로
        연환산. Merton 모형의 σ_E 입력으로 직접 사용 가능. NaN/None 자동
        제거.

    Args:
        returns: 일별 수익률 (decimal, 0.01 = 1%). None/NaN/inf 제거됨.
        tradingDays: 연환산 인자. 미국/한국 시장 기본 252. 가상자산 365.

    Returns:
        float: σ_E (연환산 변동성, decimal). 유효 샘플 < 20 시 ``0.0``.

    Raises:
        없음.

    Example:
        >>> returns = [0.01, -0.005, 0.002, ...]  # 252 일
        >>> sigma = calcEquityVolatility(returns)
        >>> 0.10 < sigma < 0.50  # 일반 주식 연 10~50% 변동성
        True

    Guide:
        sample std × √(거래일수). 최소 20 일 sample 미만 시 0 반환 →
        ``solveMerton`` 호출자가 입력 fallback 으로 사용 가능.

    SeeAlso:
        - ``solveMerton`` — 본 함수 결과를 σ_E 입력으로 받음
        - ``dartlab.synth.stats.rollingStd`` (rolling 버전)

    Requires:
        수치 입력 (decimal). 퍼센트 (%) 단위면 미리 /100 변환.

    AIContext:
        반환값 0.0 은 "샘플 부족" 신호 (negative volatility 는 불가능).
        호출자는 0.0 발견 시 외부 fallback (industry median 등) 사용
        권장.

    LLM Specifications:
        AntiPatterns:
            - 퍼센트 (e.g., 1.0 = 1%) 를 입력하지 말 것. decimal (0.01) 이
              ground truth. 결과가 비현실적 (>5.0) 이면 단위 오류 의심.
            - tradingDays 를 365 로 두고 주식 데이터 사용 금지 (15% 과대).
        OutputSchema:
            float (decimal, e.g., 0.30 = 30%).
        Prerequisites:
            len(filtered returns) ≥ 20.
        Freshness:
            입력 returns 의 freshness (보통 EOD).
        Dataflow:
            returns → filter finite → mean → sample variance (ddof=1)
            → √var → ×√tradingDays.
        TargetMarkets: 모든 시장. tradingDays 만 시장별 조정.
    """
    clean = [r for r in returns if r is not None and math.isfinite(r)]
    n = len(clean)
    if n < 20:
        return 0.0

    mean = sum(clean) / n
    variance = sum((r - mean) ** 2 for r in clean) / (n - 1)
    daily_vol = math.sqrt(variance)
    return daily_vol * math.sqrt(tradingDays)


def solveMerton(
    equityValue: float,
    debtFaceValue: float,
    equityVolatility: float,
    riskFreeRate: float = 0.035,
    maturity: float = 1.0,
    maxIter: int = 200,
    tol: float = 1e-8,
) -> MertonResult | None:
    """Merton 구조 모형 2-방정식 Newton-Raphson 풀이 → D2D + PD.

    Capabilities:
        시가총액 E, 부채 D, 주식 변동성 σ_E 에서 기업 자산가치 V 와 자산
        변동성 σ_A 를 풀어 Distance to Default 와 부도확률 (%) 을 산출.
        Moody's KMV 가 사용하는 사실상 표준 구조 모형.

    Args:
        equityValue: E — 시가총액 (원/달러).
        debtFaceValue: D — 총부채 액면가 (원/달러). 만기 T 시점 상환 의무.
        equityVolatility: σ_E — 연환산 주식 변동성 (decimal, 0.30 = 30%).
        riskFreeRate: r — 무위험이자율 (decimal). 기본 0.035 (3.5%).
        maturity: T — 만기 (년). 기본 1.0.
        maxIter: Newton-Raphson 최대 반복. 기본 200.
        tol: 수렴 허용오차. 기본 1e-8.

    Returns:
        MertonResult | None:
            - ``assetValue`` (float): V — 추정 기업 자산가치
            - ``assetVolatility`` (float): σ_A — 자산 변동성
            - ``d2d`` (float): Distance to Default (시그마 단위)
            - ``pd`` (float): 부도확률 (%, 0~100)
            - ``equityValue``/``debtFaceValue``/``riskFreeRate``/
              ``maturity``/``equityVolatility``: 입력 echo
            - ``converged`` (bool): Newton-Raphson 수렴 여부
            - ``iterations`` (int): 실제 반복 횟수
        입력 부적절 (E≤0, D≤0, σ_E≤0) 시 ``None``.

    Raises:
        없음 — 수렴 실패 시 ``converged=False`` 로 반환.

    Example:
        >>> r = solveMerton(equityValue=1e12, debtFaceValue=5e11,
        ...                 equityVolatility=0.30)
        >>> if r and r.converged:
        ...     print(f"PD: {r.pd:.2f}%, D2D: {r.d2d:.2f}σ")

    Guide:
        Merton (1974, JF). 기업 자산 V 가 GBM 따른다고 가정 →
        E = V·N(d₁) - D·e^(-rT)·N(d₂) (Black-Scholes call). 추가 제약
        σ_E·E = V·N(d₁)·σ_A (Itô) 와 함께 2-방정식 풀이. D2D = (ln(V/D) +
        (r - σ_A²/2)·T) / (σ_A·√T), PD = N(-D2D).

    SeeAlso:
        - ``calcEquityVolatility`` — σ_E 입력 준비
        - ``dartlab.synth.distress.chsModel.calcCHS`` — alternative PD

    Requires:
        E > 0, D > 0, σ_E > 0, T > 0.

    AIContext:
        ``converged=False`` 결과의 d2d/pd 는 신뢰도 낮음. 호출자는
        converged 필터링 후 사용 권장. d2d < 0 은 즉시 부도 위험, d2d > 4
        는 매우 안전.

    LLM Specifications:
        AntiPatterns:
            - σ_E 를 퍼센트 단위 (30) 로 입력 금지. decimal (0.30) 만.
            - 단기 부채만으로 D 산정 금지. 본 모형은 만기 T 까지의 모든
              상환 의무를 합친 face value 가정.
            - converged=False 인데 pd 단독 인용 금지.
        OutputSchema:
            MertonResult dataclass (slots=True). 11 필드 모두 출력.
        Prerequisites:
            E > 0, D > 0, σ_E > 0, 0 < T ≤ 10.
        Freshness:
            E = 거래일 종가, D = 최신 BS 분기, σ_E = 30~252 일 rolling.
        Dataflow:
            initial guess (V=E+D, σ_A=σ_E·E/(E+D)) → Newton-Raphson
            (자코비안 2x2) → 수렴 후 d2d/pd 계산.
        TargetMarkets: Global. 신흥국은 D 의 외화 부채 분리 권장.
    """
    # norm.cdf/pdf → _norm_cdf/_norm_pdf (math.erf 기반, scipy 불필요)

    E = equityValue
    D = debtFaceValue
    sigma_E = equityVolatility

    if E <= 0 or D <= 0 or sigma_E <= 0 or maturity <= 0:
        return None

    sqrtT = math.sqrt(maturity)
    expRT = math.exp(-riskFreeRate * maturity)

    # 초기값
    V = E + D
    sigma_A = sigma_E * E / (E + D)

    for i in range(maxIter):
        if V <= 0 or sigma_A <= 0:
            return MertonResult(
                assetValue=V,
                assetVolatility=sigma_A,
                d2d=0.0,
                pd=100.0,
                equityValue=E,
                debtFaceValue=D,
                riskFreeRate=riskFreeRate,
                maturity=maturity,
                equityVolatility=sigma_E,
                converged=False,
                iterations=i,
            )

        d1 = (math.log(V / D) + (riskFreeRate + 0.5 * sigma_A**2) * maturity) / (sigma_A * sqrtT)
        d2 = d1 - sigma_A * sqrtT

        Nd1 = _normCdf(d1)
        Nd2 = _normCdf(d2)
        nd1 = _normPdf(d1)

        # f1: E - V·N(d1) + D·e^(-rT)·N(d2) = 0
        f1 = E - V * Nd1 + D * expRT * Nd2
        # f2: σ_E·E - V·N(d1)·σ_A = 0
        f2 = sigma_E * E - V * Nd1 * sigma_A

        # 야코비안
        # ∂f1/∂V = -N(d1) - V·n(d1)·∂d1/∂V + D·e^(-rT)·n(d2)·∂d2/∂V
        # ∂d1/∂V = 1 / (V·σ_A·√T)
        dd1_dV = 1.0 / (V * sigma_A * sqrtT)
        dd2_dV = dd1_dV

        J11 = -Nd1  # ∂f1/∂V (simplified: higher order terms cancel)
        J12 = D * expRT * nd1 * sqrtT  # ∂f1/∂σ_A (via d2)
        # Actually compute full Jacobian
        J11 = -Nd1 - V * nd1 * dd1_dV + D * expRT * nd1 * dd2_dV  # nd1 = n(d1) ≈ n(d2) only at d1≈d2
        # Correct: n(d2) ≠ n(d1) in general
        nd2 = _normPdf(d2)
        J11 = -Nd1 - V * nd1 * dd1_dV + D * expRT * nd2 * dd2_dV

        dd1_dsA = -(math.log(V / D) + (riskFreeRate - 0.5 * sigma_A**2) * maturity) / (sigma_A**2 * sqrtT)
        dd2_dsA = dd1_dsA - sqrtT

        J12 = -V * nd1 * dd1_dsA + D * expRT * nd2 * dd2_dsA

        # ∂f2/∂V = -N(d1)·σ_A - V·n(d1)·∂d1/∂V·σ_A
        J21 = -Nd1 * sigma_A - V * nd1 * dd1_dV * sigma_A
        # ∂f2/∂σ_A = -V·N(d1) - V·n(d1)·∂d1/∂σ_A·σ_A
        J22 = -V * Nd1 - V * nd1 * dd1_dsA * sigma_A

        # 행렬식
        det = J11 * J22 - J12 * J21
        if abs(det) < 1e-20:
            break

        # Newton step
        dV = (f1 * J22 - f2 * J12) / det
        dSigma = (J11 * f2 - J21 * f1) / det

        V_new = V - dV
        sigma_new = sigma_A - dSigma

        # 양수 보장 (step halving)
        step = 1.0
        while (V_new <= 0 or sigma_new <= 0) and step > 1e-4:
            step *= 0.5
            V_new = V - dV * step
            sigma_new = sigma_A - dSigma * step

        if V_new <= 0 or sigma_new <= 0:
            break

        V = V_new
        sigma_A = sigma_new

        if abs(dV) < tol * V and abs(dSigma) < tol * sigma_A:
            # 수렴
            (math.log(V / D) + (riskFreeRate + 0.5 * sigma_A**2) * maturity) / (sigma_A * sqrtT)
            d2d = (math.log(V / D) + (riskFreeRate - 0.5 * sigma_A**2) * maturity) / (sigma_A * sqrtT)
            pd_pct = _normCdf(-d2d) * 100

            return MertonResult(
                assetValue=V,
                assetVolatility=sigma_A,
                d2d=d2d,
                pd=pd_pct,
                equityValue=E,
                debtFaceValue=D,
                riskFreeRate=riskFreeRate,
                maturity=maturity,
                equityVolatility=sigma_E,
                converged=True,
                iterations=i + 1,
            )

    # 미수렴 — 마지막 값으로 D2D 계산
    if V > 0 and sigma_A > 0:
        d2d = (math.log(V / D) + (riskFreeRate - 0.5 * sigma_A**2) * maturity) / (sigma_A * sqrtT)
        pd_pct = _normCdf(-d2d) * 100
    else:
        d2d = 0.0
        pd_pct = 100.0

    return MertonResult(
        assetValue=V,
        assetVolatility=sigma_A,
        d2d=d2d,
        pd=pd_pct,
        equityValue=E,
        debtFaceValue=D,
        riskFreeRate=riskFreeRate,
        maturity=maturity,
        equityVolatility=sigma_E,
        converged=False,
        iterations=maxIter,
    )
