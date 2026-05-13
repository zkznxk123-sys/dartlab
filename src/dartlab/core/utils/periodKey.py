"""공시 보고서명에서 period key 를 추출하는 L0 primitive."""

from __future__ import annotations

import re

_RE_YEAR_MONTH = re.compile(r"\((\d{4})\.(\d{2})\)")


def parsePeriodKey(reportType: str) -> str | None:
    """DART report_type 문자열에서 ``YYYYQn`` period key 를 추출한다."""
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
