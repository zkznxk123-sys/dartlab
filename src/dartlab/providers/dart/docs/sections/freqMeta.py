"""sections row 의 빈도 메타 — annual / Q1~Q4 / mixed.

각 row 가 어떤 period 들에 값을 가지는지 보고 freqKey / freqScope /
annualPeriodCount / quarterlyPeriodCount / latestAnnualPeriod /
latestQuarterlyPeriod 6 필드를 계산.

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수들을 re-import.
"""

from __future__ import annotations


def _periodFreq(period: str) -> str:
    if period.endswith("Q1"):
        return "q1"
    if period.endswith("Q2"):
        return "q2"
    if period.endswith("Q3"):
        return "q3"
    if period.endswith("Q4"):
        return "q4"
    return "annual"


def _freqSortKey(freq: str) -> int:
    return {"annual": 0, "q1": 1, "q2": 2, "q3": 3, "q4": 4}.get(freq, 9)


def _rowFreqMeta(periodMap: dict[str, str]) -> dict[str, object]:
    annualPeriods: list[str] = []
    quarterlyPeriods: list[str] = []
    for period, value in periodMap.items():
        if not isinstance(value, str) or not value.strip():
            continue
        suffix = period[-2:]
        if suffix in ("Q1", "Q2", "Q3", "Q4"):
            quarterlyPeriods.append(period)
        else:
            annualPeriods.append(period)

    annualCount = len(annualPeriods)
    quarterlyCount = len(quarterlyPeriods)

    if annualCount == 0 and quarterlyCount == 0:
        return {
            "freqKey": "none",
            "freqScope": "none",
            "annualPeriodCount": 0,
            "quarterlyPeriodCount": 0,
            "latestAnnualPeriod": None,
            "latestQuarterlyPeriod": None,
        }

    if annualCount > 0 and quarterlyCount > 0:
        freqScope = "mixed"
    elif annualCount > 0:
        freqScope = "annual"
    else:
        freqScope = "quarterly"

    freqKeys: list[str] = []
    if annualCount > 0:
        freqKeys.append("annual")
    freqSet = set()
    for p in quarterlyPeriods:
        c = _periodFreq(p)
        if c not in freqSet:
            freqSet.add(c)
            freqKeys.append(c)
    freqKeys.sort(key=_freqSortKey)

    latestAnnual = max(annualPeriods) if annualPeriods else None
    latestQuarterly = max(quarterlyPeriods) if quarterlyPeriods else None

    return {
        "freqKey": ",".join(freqKeys),
        "freqScope": freqScope,
        "annualPeriodCount": annualCount,
        "quarterlyPeriodCount": quarterlyCount,
        "latestAnnualPeriod": latestAnnual,
        "latestQuarterlyPeriod": latestQuarterly,
    }
