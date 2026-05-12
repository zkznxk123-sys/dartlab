"""거버넌스 종합 등급 산출 (5축 = 100점).

배점: 지분(20) + 사외(25) + 보수(15) + 감사(25) + 분산(15)
"""

from __future__ import annotations


def scoreOwnership(pct: float | None) -> float:
    """최대주주 지분율 → 거버넌스 점수.

    30~50% 구간이 최적(20점). 과소(경영권 불안)·과대(독단 리스크) 모두 감점.
    None이면 중간값 10점을 반환한다.

    Parameters
    ----------
    pct : float | None
        최대주주 지분율 (%)

    Returns
    -------
    float
        지분율 점수 (점, 0~20)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import scoreOwnership
    >>> scoreOwnership(35.0)
    20.0
    """
    if pct is None:
        return 10.0
    if 30 <= pct <= 50:
        return 20.0
    if 20 <= pct < 30 or 50 < pct <= 60:
        return 16.0
    if 10 <= pct < 20 or 60 < pct <= 70:
        return 12.0
    if pct < 10:
        return 4.0
    return 8.0  # 70%+


def scoreOutsideRatio(
    ratio: float | None,
    *,
    resign: int = 0,
    concurrent: int = 0,
) -> float:
    """사외이사 비율 → 거버넌스 점수.

    비율이 높을수록 고점수. 중도사임(건당 -3, 최대 -6)과
    겸직(건당 -2, 최대 -4) 페널티를 차감한다.
    None이면 중간값 12.5점을 반환한다.

    Parameters
    ----------
    ratio : float | None
        사외이사 비율 (%)
    resign : int
        중도사임 인원 (명)
    concurrent : int
        겸직 인원 (명)

    Returns
    -------
    float
        사외이사 점수 (점, 0~25)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import scoreOutsideRatio
    >>> scoreOutsideRatio(45.0, resign=0, concurrent=0)
    25.0
    """
    if ratio is None:
        return 12.5

    if ratio >= 40:
        base = 25.0
    elif ratio >= 30:
        base = 22.0
    elif ratio >= 20:
        base = 18.0
    elif ratio >= 10:
        base = 14.0
    elif ratio > 0:
        base = 8.0
    else:
        base = 3.0

    penalty = 0.0
    if resign > 0:
        penalty += min(resign * 3, 6)
    if concurrent > 0:
        penalty += min(concurrent * 2, 4)

    return max(base - penalty, 0.0)


def scorePayRatio(ratio: float | None) -> float:
    """임원-직원 보수 배율 → 거버넌스 점수.

    배율이 낮을수록 고점수. 2배 이하 만점(15), 20배 초과 최저(1).
    None이면 중간값 7.5점을 반환한다.

    Parameters
    ----------
    ratio : float | None
        임원/직원 보수 배율 (배)

    Returns
    -------
    float
        보수 배율 점수 (점, 0~15)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import scorePayRatio
    >>> scorePayRatio(1.5)
    15.0
    """
    if ratio is None:
        return 7.5
    if ratio <= 2:
        return 15.0
    if ratio <= 3:
        return 13.0
    if ratio <= 5:
        return 11.0
    if ratio <= 10:
        return 8.0
    if ratio <= 20:
        return 4.0
    return 1.0


def scoreAudit(opinion: str | None) -> float:
    """감사의견 → 거버넌스 점수.

    적정의견 만점(25), 한정의견 5점, 부적정·의견거절 0점.
    None이면 중간값 12.5점을 반환한다.

    Parameters
    ----------
    opinion : str | None
        감사의견 문자열 (적정의견 | 한정의견 | 부적정의견 | 의견거절)

    Returns
    -------
    float
        감사의견 점수 (점, 0~25)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import scoreAudit
    >>> scoreAudit("적정의견")
    25.0
    """
    if opinion is None or opinion == "":
        return 12.5
    if opinion == "적정의견":
        return 25.0
    if opinion == "한정의견":
        return 5.0
    return 0.0  # 부적정의견, 의견거절


def scoreMinority(pct: float | None) -> float:
    """소액주주 지분율 → 거버넌스 점수.

    지분율이 높을수록 주주 분산이 양호하여 고점수.
    60% 이상 만점(15), 20% 미만 최저(2).
    None이면 중간값 7.5점을 반환한다.

    Parameters
    ----------
    pct : float | None
        소액주주 지분율 (%)

    Returns
    -------
    float
        소액주주 분산 점수 (점, 0~15)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import scoreMinority
    >>> scoreMinority(65.0)
    15.0
    """
    if pct is None:
        return 7.5
    if pct >= 60:
        return 15.0
    if pct >= 50:
        return 13.0
    if pct >= 40:
        return 11.0
    if pct >= 30:
        return 8.0
    if pct >= 20:
        return 5.0
    return 2.0


def grade(score: float) -> str:
    """거버넌스 총점 → 등급 변환.

    A(85+) / B(70+) / C(55+) / D(40+) / E(40 미만).

    Parameters
    ----------
    score : float
        거버넌스 종합 점수 (점, 0~100)

    Returns
    -------
    str
        등급 (A | B | C | D | E)

    Raises
    ------
    없음 — 순수 분기 함수.

    Examples
    --------
    >>> from dartlab.scan.governance.scorer import grade
    >>> grade(88.5)
    'A'
    """
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "E"
