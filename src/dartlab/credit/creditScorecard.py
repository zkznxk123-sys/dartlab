"""신용등급 산출 순수 로직.

업종별 기준표에서 각 지표를 0-100 위험 점수로 변환하고,
5축 가중평균으로 종합 점수를 산출한다. 20단계 등급(AAA~D) 매핑표는
``credit.gradeTable`` SSOT (P3.6 후 도메인 복귀).
"""

from __future__ import annotations

# 20단계 등급 매핑표 + 변환 함수는 credit 도메인 SSOT — analysis/bond 등은 단방향 import.
from dartlab.credit.gradeTable import (  # noqa: F401
    estimatePD,
    gradeCategory,
    isInvestmentGrade,
    mapTo20Grade,
    notchGrade,
)


def scoreMetric(
    value: float | None,
    thresholdDef: dict,
) -> float | None:
    """단일 지표 → 0-100 위험 점수 (선형 보간).

    thresholdDef: {"lower_is_better": bool, "breakpoints": [(value, score), ...]}
    breakpoints는 값 오름차순 정렬 가정.
    """
    if value is None:
        return None

    lower_is_better = thresholdDef["lower_is_better"]
    bps = thresholdDef["breakpoints"]

    if not bps:
        return None

    # lower_is_better=False인 지표는 값 내림차순 → 오름차순 반전
    if not lower_is_better:
        bps = [(v, s) for v, s in reversed(bps)]

    # 범위 밖 처리
    if value <= bps[0][0]:
        return bps[0][1]
    if value >= bps[-1][0]:
        return bps[-1][1]

    # 선형 보간
    for i in range(len(bps) - 1):
        v0, s0 = bps[i]
        v1, s1 = bps[i + 1]
        if v0 <= value <= v1:
            if v1 == v0:
                return s0
            ratio = (value - v0) / (v1 - v0)
            return round(s0 + ratio * (s1 - s0), 2)

    return bps[-1][1]


def weightedScore(axes: list[dict]) -> float:
    """5축 가중평균 종합 점수.

    axes: [{"name": str, "score": float|None, "weight": float}, ...]
    score가 None인 축은 제외하고 나머지 가중치를 재분배.
    """
    valid = [(a["score"], a["weight"]) for a in axes if a.get("score") is not None]
    if not valid:
        return 50.0  # 데이터 없으면 중립

    totalWeight = sum(w for _, w in valid)
    if totalWeight <= 0:
        return 50.0

    return round(sum(s * w for s, w in valid) / totalWeight, 2)


# mapTo20Grade / estimatePD / notchGrade / isInvestmentGrade / gradeCategory:
# core/cross/creditGradeTable SSOT 에서 import (모듈 상단 from 절). 중복 정의 제거.


# ── 현금흐름등급 (eCR) ──


def cashFlowGrade(
    ocf_to_sales: float | None,
    fcf_positive: bool | None,
    ocf_to_debt: float | None,
    ocf_trend_stable: bool | None = None,
) -> str:
    """현금흐름등급 eCR-1 ~ eCR-6.

    한국 신평사 현금흐름창출능력 별도 평가 대응.
    """
    if ocf_to_sales is None:
        return "eCR-?"

    # eCR-1: 최상의 현금흐름
    if ocf_to_sales > 15 and (fcf_positive is True) and (ocf_to_debt is not None and ocf_to_debt > 30):
        return "eCR-1"

    # eCR-2: 우수
    if ocf_to_sales > 10 and (ocf_to_debt is not None and ocf_to_debt > 20):
        return "eCR-2"

    # eCR-3: 양호
    if ocf_to_sales > 5 and (ocf_trend_stable is not False):
        return "eCR-3"

    # eCR-4: 보통
    if ocf_to_sales > 0:
        return "eCR-4"

    # eCR-5: 취약
    if ocf_to_sales > -5:
        return "eCR-5"

    # eCR-6: 심각
    return "eCR-6"


# ── 등급 전망 (Outlook) ──


def creditOutlook(scoreHistory: list[float]) -> str:
    """5개년 종합점수 추세 → 안정적/긍정적/부정적.

    scoreHistory: 최신→과거 순서 점수 리스트.
    """
    if not scoreHistory or len(scoreHistory) < 2:
        return "N/A"

    recent = scoreHistory[0]
    oldest = scoreHistory[-1]
    delta = recent - oldest

    # 점수 하락(개선) = 긍정적, 상승(악화) = 부정적
    if delta < -5:
        return "긍정적"
    if delta > 5:
        return "부정적"
    return "안정적"


def axisScore(
    metricScores: list,
) -> float | None:
    """축 내 개별 지표 점수들의 평균 → 축 점수.

    metricScores: [(지표명, 점수|None), ...] 또는 [{"name", "value", "score"}, ...]
    None인 지표는 제외. tuple/dict 둘 다 지원 (R21-1: metrics 에 value 포함).
    """
    valid: list[float] = []
    for item in metricScores:
        if isinstance(item, dict):
            s = item.get("score")
        else:
            _, s = item
        if s is not None:
            valid.append(s)
    if not valid:
        return None
    return round(sum(valid) / len(valid), 2)
