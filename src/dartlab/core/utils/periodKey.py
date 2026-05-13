"""공시 보고서명에서 period key 를 추출하는 L0 primitive."""

from __future__ import annotations

import re

_RE_YEAR_MONTH = re.compile(r"\((\d{4})\.(\d{2})\)")


def parsePeriodKey(reportType: str) -> str | None:
    """DART report_type 문자열에서 ``YYYYQn`` period key 를 추출한다.

    Capabilities:
        DART 보고서명에 포함된 ``(YYYY.MM)`` 표기를 표준 분기 key로 바꾼다.
    AIContext:
        공시/재무 데이터가 같은 period key로 join되도록 하는 L0 parser primitive.
    Guide:
        DART report_type 문자열 전용이다. EDGAR/EDINET period 표준화는 별도 mapper를 둔다.
    When:
        report selector나 parser가 보고서명을 기준으로 분기 key를 보강할 때.
    How:
        괄호 안 연월을 정규식으로 추출하고 보고서 종류와 월을 매칭해 Q1~Q4로 변환한다.
    Args:
        reportType: DART report_type 문자열.
    Returns:
        ``YYYYQ1``~``YYYYQ4`` 또는 파싱 불가 시 ``None``.
    Requires:
        보고서명에 ``(YYYY.MM)`` 패턴이 포함되어야 한다.
    Raises:
        없음.
    Example:
        >>> parsePeriodKey("분기보고서 (2024.03)")
        '2024Q1'
    SeeAlso:
        ``dartlab.providers.reportSelector``.
    """
    m = _RE_YEAR_MONTH.search(reportType)
    if not m:
        return None

    year = m.group(1)
    month = m.group(2)

    if "분기보고서" in reportType:
        if month == "03":
            return f"{year}Q1"
        if month == "09":
            return f"{year}Q3"
    elif "반기보고서" in reportType:
        return f"{year}Q2"
    elif "사업보고서" in reportType:
        return f"{year}Q4"
    return None
