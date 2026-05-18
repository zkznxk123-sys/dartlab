"""crossRegression 의 fit — fitCrossSection · fitPanel · _winsorizeObs."""

from __future__ import annotations

import logging

from dartlab.analysis.valuation._crossRegressionTypes import (
    CompanyFeatures,
    CrossSectionModel,
    PanelModel,
)
from dartlab.core.utils.ols import olsMulti as _olsMulti

log = logging.getLogger(__name__)

FEATURES = [
    "per",
    "pbr",
    "lnMarketCap",
    "operatingMargin",
    "capexRatio",
    "debtRatio",
    "foreignHoldingRatio",
    "revenueGrowthLag",
]


def fitCrossSection(
    observations: list[CompanyFeatures],
    *,
    minObs: int = 30,
    winsorize: float = 0.02,
) -> CrossSectionModel | None:
    """전 상장사 횡단면 회귀 적합.

    Parameters
    ----------
    observations : list[CompanyFeatures]
        같은 연도의 CompanyFeatures 리스트.
    minObs : int
        최소 관측치 수 (기본 30).
    winsorize : float
        양쪽 꼬리 절사 비율 (기본 0.02 = 2%).

    Returns
    -------
    CrossSectionModel | None
        year : int — 적합 연도
        coefficients : list[float] — 회귀계수 [절편, beta1, ...]
        rSquared : float — 결정계수 (0~1)
        adjRSquared : float — 수정 결정계수 (0~1)
        nObs : int — 관측치 수
        관측치 부족 시 None.

    Capabilities:
        - 횡단면 회귀 (전 상장사) OLS + 섹터 더미 + winsorize → 모델 추정
        - R²/AdjR² 동시 평가

    Guide:
        Fama-MacBeth 횡단면 표준. winsorize 2% 로 outlier 영향 축소.

    When:
        횡단면 모델 학습 + AI "전 시장에서 이 변수 효과" 답변.

    How:
        winsorize → OLS via numpy → 모델 dataclass.

    Requires:
        같은 연도 observations ≥ minObs (기본 30).

    Raises:
        없음 — 부족 시 None.

    Example:
        >>> m = fitCrossSection(obs); m.rSquared
        0.32

    See Also:
        - fitPanel : 패널 (다년)
        - saveModel : 저장

    AIContext:
        "PER 가 매출 성장 예측에" 답변 시 coefficients + R² 인용.
    """
    if len(observations) < minObs:
        return None

    year = observations[0].year

    # 이상치 제거 (winsorize)
    obs = _winsorizeObs(observations, winsorize)

    # 섹터 더미 구성
    sectors = sorted({o.sector for o in obs if o.sector})
    sectors[0] if sectors else ""
    sectorDummies = sectors[1:] if len(sectors) > 1 else []

    # X, y 구성
    X: list[list[float]] = []
    y: list[float] = []
    for o in obs:
        row = o.toFeatureVector()
        # 섹터 더미 추가
        for sd in sectorDummies:
            row.append(1.0 if o.sector == sd else 0.0)
        X.append(row)
        y.append(o.revenueGrowth)

    # OLS 적합
    result = _olsMulti(X, y, addIntercept=True)
    if result is None:
        return None

    featureNames = list(FEATURES) + sectorDummies
    warnings: list[str] = []
    if result.rSquared < 0.05:
        warnings.append(f"R² 매우 낮음 ({result.rSquared:.3f}) — 예측력 제한적")

    return CrossSectionModel(
        year=year,
        coefficients=result.coefficients,
        featureNames=featureNames,
        rSquared=result.rSquared,
        adjRSquared=result.adjRSquared,
        nObs=result.nObs,
        sectorNames=sectorDummies,
        warnings=warnings,
    )


# ══════════════════════════════════════════════════════════
# 패널 회귀 적합 (기업 고정효과)
# ══════════════════════════════════════════════════════════


def fitPanel(
    observations: list[CompanyFeatures],
    *,
    minObs: int = 50,
    minYears: int = 3,
) -> PanelModel | None:
    """패널 회귀 (within estimator -- 기업 고정효과).

    각 변수에서 기업 평균을 빼고(demean) OLS 적합.
    기업별 절편(alpha_i) = 기업 평균 y - beta * 기업 평균 X.

    Parameters
    ----------
    observations : list[CompanyFeatures]
        여러 연도의 CompanyFeatures 리스트.
    minObs : int
        최소 관측치 수 (기본 50).
    minYears : int
        최소 연도 수 (기본 3).

    Returns
    -------
    PanelModel | None
        coefficients : list[float] — 회귀계수 (절편 없음, demeaned)
        rSquared : float — 결정계수 (0~1)
        nObs : int — 관측치 수
        nFirms : int — 기업 수
        firmIntercepts : dict[str, float] — 기업별 고정효과
        관측치/연도 부족 시 None.

    Capabilities:
        - within estimator (demeaning) → 기업 고정효과 + 변수 효과 분리 추정
        - firmIntercepts 종목별 α_i

    Guide:
        횡단면 OLS 보다 omitted variable bias 강건. minObs 50 + minYears 3.

    When:
        패널 모델 추정 + AI 다년 효과 답변.

    How:
        기업별 평균 demeaning → OLS → 기업별 intercept 복원.

    Requires:
        observations ≥ 50 + 연도 ≥ 3 + 기업당 ≥ 2 관측.

    Raises:
        없음 — 부족 시 None.

    Example:
        >>> p = fitPanel(obs); p.rSquared
        0.42

    See Also:
        - fitCrossSection : 단일 연도
        - savePanelModel : 저장

    AIContext:
        "기업 고정효과 분리한 변수 효과" 답변 시 coefficients + nFirms 인용.
    """
    if len(observations) < minObs:
        return None

    years = {o.year for o in observations}
    if len(years) < minYears:
        return None

    # 기업별 그룹핑
    firmObs: dict[str, list[CompanyFeatures]] = {}
    for o in observations:
        firmObs.setdefault(o.stockCode, []).append(o)

    # 기업별 평균 계산 + demeaning
    xDemeaned: list[list[float]] = []
    yDemeaned: list[float] = []
    firmMeanY: dict[str, float] = {}
    firmMeanX: dict[str, list[float]] = {}

    for code, oList in firmObs.items():
        if len(oList) < 2:
            continue

        # 기업 평균
        nF = len(FEATURES)
        meanX = [0.0] * nF
        meanY = 0.0
        for o in oList:
            vec = o.toFeatureVector()
            for j in range(nF):
                meanX[j] += vec[j]
            meanY += o.revenueGrowth
        cnt = len(oList)
        if cnt == 0:
            continue
        meanX = [v / cnt for v in meanX]
        meanY /= cnt

        firmMeanY[code] = meanY
        firmMeanX[code] = meanX

        # demeaning
        for o in oList:
            vec = o.toFeatureVector()
            xDemeaned.append([vec[j] - meanX[j] for j in range(nF)])
            yDemeaned.append(o.revenueGrowth - meanY)

    if len(xDemeaned) < minObs:
        return None

    # demeaned OLS (절편 없음)
    result = _olsMulti(xDemeaned, yDemeaned, addIntercept=False)
    if result is None:
        return None

    # 기업별 절편 복원: αi = meanY_i - β · meanX_i
    firmIntercepts: dict[str, float] = {}
    for code in firmMeanY:
        alpha = firmMeanY[code]
        for j, beta in enumerate(result.coefficients):
            alpha -= beta * firmMeanX[code][j]
        firmIntercepts[code] = alpha

    grandMean = sum(firmMeanY.values()) / len(firmMeanY) if firmMeanY else 0.0

    return PanelModel(
        coefficients=result.coefficients,
        featureNames=list(FEATURES),
        rSquared=result.rSquared,
        nObs=result.nObs,
        nFirms=len(firmMeanY),
        firmIntercepts=firmIntercepts,
        grandMean=grandMean,
    )


# ══════════════════════════════════════════════════════════
# 모델 캐시 (일 1회 사전 적합 → JSON → 즉시 로드)
# ══════════════════════════════════════════════════════════


def _winsorizeObs(
    obs: list[CompanyFeatures],
    pct: float,
) -> list[CompanyFeatures]:
    """종속변수(revenueGrowth) 양쪽 꼬리 절사."""
    if pct <= 0 or len(obs) < 10:
        return obs

    growths = sorted(o.revenueGrowth for o in obs)
    n = len(growths)
    loIdx = max(int(n * pct), 1)
    hiIdx = min(int(n * (1 - pct)), n - 1)
    lo = growths[loIdx]
    hi = growths[hiIdx]

    return [o for o in obs if lo <= o.revenueGrowth <= hi]
