"""crossRegression 의 dataclass — CrossSectionModel/PanelModel/CompanyFeatures."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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


@dataclass
class CrossSectionModel:
    """횡단면 회귀 모델 — 사전 적합 결과."""

    year: int
    coefficients: list[float]  # [intercept, β1, β2, ..., β_sector1, ...]
    featureNames: list[str]  # FEATURES + 섹터 더미 이름
    rSquared: float
    adjRSquared: float
    nObs: int
    sectorNames: list[str]  # 섹터 더미로 사용된 섹터 목록 (첫 번째 제외 = reference)
    warnings: list[str] = field(default_factory=list)

    def predict(self, features: dict[str, float], sector: str = "") -> float | None:
        """개별 기업의 매출 성장률 예측.

        Parameters
        ----------
        features : dict[str, float]
            FEATURES 목록과 동일한 키의 피처 dict.
        sector : str
            WICS 업종명 (sectorNames에 있으면 해당 더미 1, 아니면 0).

        Returns
        -------
        float | None
            예측 매출 성장률 (%). 피처 누락 시 None.

        Capabilities:
            - features dict + 섹터 더미 → linear combination 매출 성장률 예측
            - sector 가 sectorNames 에 없으면 reference (모든 더미 0)

        Guide:
            CrossSectionModel 의 predict — fitCrossSection 결과 모델 인스턴스에서 호출.

        When:
            모델 추정 후 개별 기업 예측 + AI 매출 성장 예측 답변.

        How:
            FEATURES 추출 → 섹터 더미 append → β·x 합산.

        Requires:
            features 에 FEATURES 모든 key + 적합된 coefficients.

        Raises:
            없음 — 누락 시 None.

        Example:
            >>> model.predict({"per": 12, ...}, sector="반도체")
            8.5

        See Also:
            - fitCrossSection : 모델 적합
            - PanelModel.predict : 패널 버전

        AIContext:
            "이 기업 매출 성장 예측" 답변 시 예측값 인용.
        """
        if not self.coefficients:
            return None

        x = []
        for fname in FEATURES:
            v = features.get(fname)
            if v is None:
                return None
            x.append(v)

        # 섹터 더미
        for sname in self.sectorNames:
            x.append(1.0 if sector == sname else 0.0)

        if len(x) + 1 != len(self.coefficients):
            log.debug("피처 수 불일치: x=%d, coeffs=%d", len(x) + 1, len(self.coefficients))
            return None

        # intercept + β·x
        pred = self.coefficients[0]
        for i, xi in enumerate(x):
            pred += self.coefficients[i + 1] * xi

        return pred


@dataclass
class PanelModel:
    """패널 회귀 모델 (기업 고정효과)."""

    coefficients: list[float]  # [β1, β2, ...] (절편 없음 — demeaned)
    featureNames: list[str]
    rSquared: float
    nObs: int
    nFirms: int
    firmIntercepts: dict[str, float]  # 기업별 절편 (고정효과)
    grandMean: float  # 전체 평균 성장률

    def predict(self, stockCode: str, features: dict[str, float]) -> float | None:
        """기업 고정효과 + 변수 효과로 매출 성장률 예측.

        Parameters
        ----------
        stockCode : str
            종목코드 (고정효과 조회용).
        features : dict[str, float]
            FEATURES 목록과 동일한 키의 피처 dict.

        Returns
        -------
        float | None
            예측 매출 성장률 (%). 피처 누락 시 None.

        Capabilities:
            - 기업 고정효과 + 변수 효과 → 예측 (firmIntercepts[code] 또는 grandMean fallback)
            - 패널 회귀 결과 활용

        Guide:
            기업 고정효과 (firmIntercepts) 추정으로 횡단면보다 정확. 신규 종목은 grandMean.

        When:
            패널 모델 적합 후 예측 + AI 패널 회귀 답변.

        How:
            firmIntercepts lookup → β·x 가산.

        Requires:
            features key = featureNames + 모델 적합 완료.

        Raises:
            없음.

        Example:
            >>> panel.predict("005930", {...})
            7.2

        See Also:
            - fitPanel : 패널 모델 적합
            - CrossSectionModel.predict : 횡단면

        AIContext:
            패널 fixed effects 인용한 예측 답변.
        """
        x = []
        for fname in self.featureNames:
            v = features.get(fname)
            if v is None:
                return None
            x.append(v)

        if len(x) != len(self.coefficients):
            return None

        alpha = self.firmIntercepts.get(stockCode, self.grandMean)
        pred = alpha
        for i, xi in enumerate(x):
            pred += self.coefficients[i] * xi
        return pred


@dataclass
class CompanyFeatures:
    """횡단면/패널 회귀에 사용할 기업별 피처."""

    stockCode: str
    year: int
    sector: str
    revenueGrowth: float  # 종속변수: 매출 성장률 (%)
    per: float
    pbr: float
    lnMarketCap: float
    operatingMargin: float
    capexRatio: float
    debtRatio: float
    foreignHoldingRatio: float
    revenueGrowthLag: float  # 전년 매출 성장률

    def toFeatureDict(self) -> dict[str, float]:
        """FEATURES 순서에 맞는 dict 반환.

        Returns
        -------
        dict[str, float]
            피처명 → 값 매핑 (per, pbr, lnMarketCap 등).

        Requires:
            CompanyFeatures 모든 필드 채워짐.

        Raises:
            없음.

        Example:
            >>> cf.toFeatureDict()["per"]
            12.5
        """
        return {
            "per": self.per,
            "pbr": self.pbr,
            "lnMarketCap": self.lnMarketCap,
            "operatingMargin": self.operatingMargin,
            "capexRatio": self.capexRatio,
            "debtRatio": self.debtRatio,
            "foreignHoldingRatio": self.foreignHoldingRatio,
            "revenueGrowthLag": self.revenueGrowthLag,
        }

    def toFeatureVector(self) -> list[float]:
        """FEATURES 순서의 float 리스트.

        Returns
        -------
        list[float]
            FEATURES 순서대로 정렬된 피처 값 리스트.

        Requires:
            CompanyFeatures 필드 채워짐.

        Raises:
            없음.

        Example:
            >>> cf.toFeatureVector()[0]
            12.5
        """
        d = self.toFeatureDict()
        return [d[f] for f in FEATURES]


# ══════════════════════════════════════════════════════════
# 횡단면 회귀 적합
# ══════════════════════════════════════════════════════════
