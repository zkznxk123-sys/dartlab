"""재무 데이터 품질 점수.

finance 시계열의 완전성을 3가지 지표로 측정:
- mappingRate: 원본 계정 중 매핑된 비율
- periodCoverage: 기간별 데이터 존재 비율
- statementCompleteness: 핵심 계정(BS/IS/CF) 존재 여부
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 재무제표별 핵심 계정 — 이 계정들이 있어야 "완전한" 재무제표
_CORE_ACCOUNTS = {
    "BS": [
        "total_assets",
        "total_liabilities",
        "total_stockholders_equity",
        "cash_and_cash_equivalents",
        "current_assets",
        "current_liabilities",
    ],
    "IS": [
        "sales",
        "operating_profit",
        "net_profit",
        "cost_of_goods_sold",
    ],
    "CF": [
        "operating_cashflow",
        "investing_cashflow",
        "financing_cashflow",
    ],
}


@dataclass
class DataQualityScore:
    """재무 데이터 품질 점수."""

    mappingRate: float | None = None
    periodCoverage: float = 0.0
    statementCompleteness: dict[str, float] = field(default_factory=dict)
    missingCore: dict[str, list[str]] = field(default_factory=dict)
    totalAccounts: int = 0
    mappedAccounts: int = 0
    totalPeriods: int = 0
    coveredPeriods: int = 0

    @property
    def overallScore(self) -> float:
        """종합 품질 점수 (0~100).

        Capabilities:
            - 매핑률·기간 커버리지·완전성 단일 점수 합성.

        Guide:
            None 슬롯은 무시한 산술 평균.

        When:
            UI/리포트 "데이터 품질 N/100" 카드 표시 직전.

        How:
            mappingRate·periodCoverage·avg(completeness) 평균.

        Requires:
            DataQualityScore 인스턴스 필드 채워져 있어야.

        Raises:
            없음 (필드 부재 시 0.0).

        Example:
            >>> DataQualityScore(periodCoverage=80.0).overallScore
            80.0

        See Also:
            - computeQuality : 인스턴스 생성

        AIContext:
            AI 답변 헤더에 "데이터 품질 X/100" 표시에 직접 사용.
        """
        scores = []
        if self.mappingRate is not None:
            scores.append(self.mappingRate)
        scores.append(self.periodCoverage)
        if self.statementCompleteness:
            avg_completeness = sum(self.statementCompleteness.values()) / len(self.statementCompleteness)
            scores.append(avg_completeness)
        return sum(scores) / len(scores) if scores else 0.0

    def __repr__(self) -> str:
        lines = [f"[데이터 품질 점수: {self.overallScore:.0f}/100]"]
        if self.mappingRate is not None:
            lines.append(f"  매핑률: {self.mappingRate:.1f}% ({self.mappedAccounts}/{self.totalAccounts})")
        lines.append(f"  기간 커버리지: {self.periodCoverage:.1f}% ({self.coveredPeriods}/{self.totalPeriods})")
        for sj, pct in sorted(self.statementCompleteness.items()):
            missing = self.missingCore.get(sj, [])
            suffix = f" (누락: {', '.join(missing)})" if missing else ""
            lines.append(f"  {sj} 완전성: {pct:.0f}%{suffix}")
        return "\n".join(lines)


def computeQuality(
    series: dict[str, dict[str, list[float | None]]],
    periods: list[str],
    *,
    mappingStats: tuple[int, int] | None = None,
) -> DataQualityScore:
    """재무 시계열의 품질 점수를 계산.

    Args:
        series: buildTimeseries() 결과 — {"BS": {snakeId: [값...]}, ...}
        periods: 기간 리스트
        mappingStats: (매핑된 계정 수, 전체 계정 수) — pivot에서 전달

    Returns:
        DataQualityScore

    Capabilities:
        - mapping/coverage/completeness 3 신호 합성 점수 계산.

    Guide:
        매핑률 + 기간 커버리지 + BS/IS/CF 핵심 계정 완전성.

    When:
        timeseries 빌드 직후 품질 게이트가 필요할 때.

    How:
        series 순회 → 핵심 계정 누락 검사 → DataQualityScore 채움.

    Requires:
        buildTimeseries series + periods.

    Raises:
        없음.

    Example:
        >>> computeQuality(series, periods).overallScore
        85.0

    See Also:
        - DataQualityScore.overallScore : 합성 점수
        - buildTimeseries : series 생성

    AIContext:
        AI 가 답변 신뢰도 가드: 점수 < 50 이면 "데이터 부족" 경고 부착.
    """
    score = DataQualityScore()
    score.totalPeriods = len(periods)

    # 매핑률
    if mappingStats is not None:
        mapped, total = mappingStats
        score.mappedAccounts = mapped
        score.totalAccounts = total
        score.mappingRate = (mapped / total * 100) if total > 0 else 100.0

    # 기간 커버리지: 모든 계정에서 각 기간에 값이 하나라도 있는 비율
    if periods:
        periodHasData = [False] * len(periods)
        for sjDiv in series:
            for vals in series[sjDiv].values():
                for i, v in enumerate(vals):
                    if v is not None:
                        periodHasData[i] = True
        score.coveredPeriods = sum(periodHasData)
        score.periodCoverage = score.coveredPeriods / len(periods) * 100

    # 재무제표별 핵심 계정 완전성
    for sjDiv, coreList in _CORE_ACCOUNTS.items():
        sjData = series.get(sjDiv, {})
        present = 0
        missing = []
        for acct in coreList:
            vals = sjData.get(acct)
            if vals and any(v is not None for v in vals):
                present += 1
            else:
                missing.append(acct)
        pct = (present / len(coreList) * 100) if coreList else 100.0
        score.statementCompleteness[sjDiv] = pct
        if missing:
            score.missingCore[sjDiv] = missing

    return score
