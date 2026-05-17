"""종합 요약 텍스트 + 프로필 분류."""

from __future__ import annotations

from dartlab.analysis.financial.insight.types import Anomaly, InsightResult

GRADE_SCORE = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0, "N": None}


def _josa(word: str, withBatchim: str, withoutBatchim: str) -> str:
    """한글 조사 자동 선택 (받침 유무).

    Parameters
    ----------
    word : str
        단어.
    withBatchim : str
        받침 있을 때 조사.
    withoutBatchim : str
        받침 없을 때 조사.

    Returns
    -------
    str
        단어 + 적절한 조사.
    """
    if not word:
        return word + withBatchim
    lastChar = ord(word[-1])
    if 0xAC00 <= lastChar <= 0xD7A3:
        hasBatchim = (lastChar - 0xAC00) % 28 != 0
        return word + (withBatchim if hasBatchim else withoutBatchim)
    return word + withBatchim


def _eunNeun(word: str) -> str:
    """'은/는' 조사 자동 선택."""
    return _josa(word, "은", "는")


def _iGa(word: str) -> str:
    """'이/가' 조사 자동 선택."""
    return _josa(word, "이", "가")


def _avgGrade(grades: dict[str, str]) -> float:
    """등급 평균 점수 계산 (A=4, B=3, C=2, D=1, F=0).

    Parameters
    ----------
    grades : dict[str, str]
        영역별 등급 딕셔너리.

    Returns
    -------
    float
        avgScore : float — 평균 점수 (점). 유효 등급 없으면 0.
    """
    scores = [GRADE_SCORE[g] for g in grades.values() if GRADE_SCORE.get(g) is not None]
    if not scores:
        return 0
    return sum(scores) / len(scores)


def classifyProfile(grades: dict[str, str]) -> str:
    """등급 조합으로 기업 프로필 분류.

    Capabilities:
        - 평균 점수 + 영역별 등급 조합 → 6 프로필 (premium/growth/stable/caution/
          distress/mixed) 중 하나 매핑.

    Parameters
    ----------
    grades : dict[str, str]
        영역별 등급 딕셔너리 (performance, profitability, health 등).

    Returns
    -------
    str
        profile : str — 'premium' | 'growth' | 'stable' | 'caution' | 'distress' | 'mixed'

    Guide:
        프로필은 사용자 답변 톤 (우량 vs 주의) 결정에 사용. 단일 등급보다 신호 풍부.

    When:
        analyzeFinancial 후반. 8 영역 grade 산출 직후 호출.

    How:
        평균 점수 + risk/health/profitability 등 핵심 영역 등급 조건 비교.

    Requires:
        grades dict 에 핵심 영역 (performance/profitability/health/risk/opportunity) 키.

    Raises:
        없음.

    Example:
        >>> classifyProfile({"performance": "A", "profitability": "A", "risk": "A"})
        'premium'

    See Also:
        - generateSummary: 본 프로필 사용해 톤 분기
        - analyzeRiskSummary: 'risk' 등급 산출

    AIContext:
        프로필명은 내부 키로만 사용. 사용자 답변에는 generateSummary 의 한국어 텍스트로 전달.
    """
    avgScore = _avgGrade(grades)
    perf = grades.get("performance", "C")
    profit = grades.get("profitability", "C")
    health = grades.get("health", "C")
    risk = grades.get("risk", "C")
    opp = grades.get("opportunity", "C")

    if avgScore >= 3.0 and risk in ("A", "B"):
        return "premium"
    if perf in ("A", "B") and profit in ("A", "B") and opp in ("A", "B"):
        return "growth"
    if health in ("A", "B") and risk in ("A", "B") and profit in ("A", "B"):
        return "stable"
    if risk in ("D", "F") or health == "F":
        return "caution"
    if avgScore < 1.5:
        return "distress"
    return "mixed"


def _getStrengths(insights: dict[str, InsightResult]) -> list[str]:
    """A등급 영역의 한국어 라벨 목록 추출.

    Parameters
    ----------
    insights : dict[str, InsightResult]
        영역별 인사이트 결과.

    Returns
    -------
    list[str]
        A등급 영역 라벨 리스트 (예: ['실적', '수익성']).
    """
    strengths = []
    mapping = {
        "performance": "실적",
        "profitability": "수익성",
        "health": "재무건전성",
        "cashflow": "현금흐름",
        "governance": "지배구조",
    }
    for key, label in mapping.items():
        if key in insights and insights[key].grade == "A":
            strengths.append(label)
    return strengths


def _getWeaknesses(insights: dict[str, InsightResult]) -> list[str]:
    """F등급 영역의 한국어 라벨 목록 추출.

    Parameters
    ----------
    insights : dict[str, InsightResult]
        영역별 인사이트 결과.

    Returns
    -------
    list[str]
        F등급 영역 라벨 리스트 (예: ['재무건전성']).
    """
    weaknesses = []
    mapping = {
        "performance": "실적",
        "profitability": "수익성",
        "health": "재무건전성",
        "cashflow": "현금흐름",
        "governance": "지배구조",
    }
    for key, label in mapping.items():
        if key in insights and insights[key].grade == "F":
            weaknesses.append(label)
    return weaknesses


def _getKeyMetric(insights: dict[str, InsightResult]) -> str | None:
    """핵심 지표 문장 추출 (성장/이익률/ROE 키워드 기반).

    Parameters
    ----------
    insights : dict[str, InsightResult]
        영역별 인사이트 결과.

    Returns
    -------
    str | None
        핵심 지표 설명 문장. 해당 없으면 None.
    """
    for key in ("performance", "profitability"):
        if key in insights:
            for detail in insights[key].details:
                for keyword in ("성장", "이익률", "ROE"):
                    if keyword in detail:
                        return detail
    return None


def generateSummary(
    corpName: str,
    insights: dict[str, InsightResult],
    anomalies: list[Anomaly],
    profile: str,
) -> str:
    """한국어 종합 요약 생성.

    Capabilities:
        - 프로필별 톤 분기 + 강점/약점 영역 라벨 + danger anomaly 1 건 통합 →
          2~4 문장 자연어 요약 생성.

    Parameters
    ----------
    corpName : str
        기업명.
    insights : dict[str, InsightResult]
        영역별 인사이트 결과.
    anomalies : list[Anomaly]
        이상치 탐지 결과.
    profile : str
        기업 프로필 ('premium' | 'growth' | 'stable' | 'caution' | 'distress' | 'mixed').

    Returns
    -------
    str
        summary : str — 2~4문장의 한국어 종합 요약.

    Guide:
        UI 카드 헤더 + Ask Workbench 답변 도입부에 직접 사용. 회사명 조사 자동.

    When:
        analyzeFinancial 의 최종 단계. AnalysisResult.summary 필드에 저장.

    How:
        profile 분기 → 강점/약점 라벨 추출 → keyMetric → danger anomaly 합성.

    Requires:
        insights dict (강점/약점 추출) + anomalies (danger 보강).

    Raises:
        없음.

    Example:
        >>> generateSummary("삼성전자", insights, anomalies, "premium")
        '삼성전자는 실적, 수익성 등 ...'

    See Also:
        - classifyProfile: profile 산출
        - analyzeFinancial: 상위 호출자

    AIContext:
        본 텍스트가 사용자 답변 시작. 추가 분석은 영역별 grade · anomaly · distress 인용으로 확장.
    """
    strengths = _getStrengths(insights)
    weaknesses = _getWeaknesses(insights)
    keyMetric = _getKeyMetric(insights)

    parts: list[str] = []
    nameEunNeun = _eunNeun(corpName)

    if profile == "premium":
        if strengths:
            parts.append(
                f"{nameEunNeun} {', '.join(strengths)} 등 전반적으로 우수한 재무 상태를 보이는 우량 기업입니다."
            )
        else:
            parts.append(f"{nameEunNeun} 전반적으로 우수한 재무 상태를 보이는 우량 기업입니다.")

    elif profile == "growth":
        parts.append(f"{nameEunNeun} 성장성과 수익성이 돋보이는 기업입니다.")

    elif profile == "stable":
        parts.append(f"{nameEunNeun} 안정적인 재무구조를 갖춘 기업입니다.")

    elif profile == "caution":
        if weaknesses:
            parts.append(f"{nameEunNeun} {', '.join(weaknesses)} 측면에서 주의가 필요합니다.")
        else:
            grades = {k: v.grade for k, v in insights.items()}
            riskGrade = grades.get("risk", "C")
            if riskGrade in ("D", "F"):
                parts.append(f"{nameEunNeun} 재무 리스크 요인이 존재하여 주의가 필요합니다.")
            else:
                parts.append(f"{nameEunNeun} 일부 재무 지표에서 주의가 필요합니다.")

    elif profile == "distress":
        parts.append(f"{nameEunNeun} 여러 재무 지표에서 개선이 시급한 상황입니다.")

    else:
        if strengths and weaknesses:
            parts.append(f"{nameEunNeun} {', '.join(strengths)} 양호하나 {', '.join(weaknesses)}에서 약점을 보입니다.")
        elif strengths:
            if len(strengths) == 1:
                parts.append(f"{nameEunNeun} {_iGa(strengths[0])} 양호한 기업입니다.")
            else:
                front = ", ".join(strengths[:-1])
                parts.append(f"{nameEunNeun} {front}, {_iGa(strengths[-1])} 양호한 기업입니다.")
        else:
            parts.append(f"{nameEunNeun} 전반적으로 보통 수준의 재무 상태를 보입니다.")

    if keyMetric:
        parts.append(keyMetric + ".")

    dangerAnomalies = [a for a in anomalies if a.severity == "danger"]
    if dangerAnomalies:
        topAnomaly = dangerAnomalies[0].text.split("—")[0].strip()
        parts.append(f"다만 {topAnomaly} 점에 유의해야 합니다.")
    elif len(anomalies) >= 3:
        parts.append(f"이상 신호 {len(anomalies)}건이 감지되어 모니터링이 필요합니다.")

    return " ".join(parts)
