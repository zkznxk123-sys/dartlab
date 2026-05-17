"""재무 시계열 변곡점 감지.

finance DataFrame(account × year)에서 전년 대비 급변 지점을 감지한다.
±20% = major, ±10% = minor, 부호전환 = major.

사용법::

    from dartlab.macro.cycles.inflection import detectInflections

    inflections = detectInflections(df)
    for inf in inflections:
        _log.info(f"{inf.account} {inf.year}: {inf.changeRate:+.1%} ({inf.severity})")
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

_PERIOD_RE = re.compile(r"^\d{4}$")


@dataclass
class Inflection:
    """하나의 변곡점."""

    account: str
    year: str
    prevYear: str
    prev: float
    curr: float
    changeRate: float
    severity: str


def _accountCol(df: pl.DataFrame) -> str | None:
    for candidate in ("account", "항목", "metric", "snakeId"):
        if candidate in df.columns:
            return candidate
    return None


def detectInflections(
    df: pl.DataFrame,
    *,
    majorThreshold: float = 0.20,
    minorThreshold: float = 0.10,
    minAbsValue: float = 1.0,
) -> list[Inflection]:
    """finance DataFrame에서 변곡점을 감지한다.

    Capabilities:
        finance DataFrame (account × year) 의 셀별 연도 간 변화율을 검사하여
        |change| ≥ majorThreshold (기본 20%) = major, ≥ minorThreshold (10%) =
        minor 변곡점 추출. 부호 반전은 절대 major. AI 재무 변곡점 답변 1 차.

    Args:
        df: account(행) × year(열) DataFrame. account 컬럼 자동 인식.
        majorThreshold: major 기준 (기본 0.20 = 20%).
        minorThreshold: minor 기준 (기본 0.10 = 10%).
        minAbsValue: 0 근처 노이즈 필터 (기본 1.0).

    Returns:
        list[Inflection] — account/year/prevYear/prev/curr/changeRate/severity
        (major/minor). severity 내림차순 → changeRate 내림차순 정렬.

    Example:
        >>> inflections = detectInflections(financeDf)
        >>> inflections[0].account, inflections[0].severity
        ('영업이익', 'major')

    Guide:
        majorThreshold 30%+ 로 올리면 더 의미 있는 변곡점만 (대규모 변화).
        부호 반전 (흑자→적자 등) 은 changeRate 와 무관하게 major.

    When:
        ``analyzeCorporate`` 보조 + AI 재무 변곡점 답변 + analysis/forecast 진단.

    How:
        account 컬럼 자동 탐색 → year 컬럼 sorted → 각 cell 전기 대비 변화율 →
        임계 매칭 + 부호 반전 별도 처리.

    Requires:
        finance DataFrame (long-form account × year 행렬).

    Raises:
        없음 — account/year 컬럼 없으면 빈 list.

    See Also:
        - analysis.financial.* : 변곡점 후속 분석
        - aggregateEarningsCycle : 매크로 집계

    AIContext:
        top 3 inflection (account/year/changeRate) 인용으로 "2024 영업이익 +35%
        major 변곡" 답변.

    LLM Specifications:
        AntiPatterns:
            - minAbsValue 무시 → 0 근처 노이즈 다발
            - 단일 변곡점 단정 + severity 라벨 미노출
        OutputSchema:
            list[Inflection] (7 필드).
        Prerequisites: finance DataFrame.
        Freshness: 연간/분기.
        Dataflow: df → 셀 변화율 → 임계 → 정렬.
        TargetMarkets: KR/US (계정 형식 무관).
    """
    acctCol = _accountCol(df)
    if acctCol is None:
        return []

    yearCols = sorted(
        [c for c in df.columns if _PERIOD_RE.fullmatch(c)],
    )
    if len(yearCols) < 2:
        return []

    results: list[Inflection] = []

    accounts = df[acctCol].to_list()
    # 연도 컬럼 값들을 한 번에 추출 (to_list 1회씩만)
    yearData: dict[str, list] = {c: df[c].to_list() for c in yearCols}

    for rowIdx, account in enumerate(accounts):
        if not account:
            continue
        account = str(account)

        for i in range(1, len(yearCols)):
            prevYear = yearCols[i - 1]
            currYear = yearCols[i]
            prevVal = yearData[prevYear][rowIdx]
            currVal = yearData[currYear][rowIdx]

            if prevVal is None or currVal is None:
                continue
            try:
                prev = float(prevVal)
                curr = float(currVal)
            except (ValueError, TypeError):
                continue

            if prev != 0 and curr != 0 and (prev > 0) != (curr > 0):
                results.append(
                    Inflection(
                        account=account,
                        year=currYear,
                        prevYear=prevYear,
                        prev=prev,
                        curr=curr,
                        changeRate=0.0,
                        severity="major",
                    )
                )
                continue

            if abs(prev) < minAbsValue:
                continue

            changeRate = (curr - prev) / abs(prev)

            if abs(changeRate) >= majorThreshold:
                severity = "major"
            elif abs(changeRate) >= minorThreshold:
                severity = "minor"
            else:
                continue

            results.append(
                Inflection(
                    account=account,
                    year=currYear,
                    prevYear=prevYear,
                    prev=prev,
                    curr=curr,
                    changeRate=changeRate,
                    severity=severity,
                )
            )

    severityOrder = {"major": 0, "minor": 1}
    results.sort(key=lambda x: (severityOrder.get(x.severity, 9), -abs(x.changeRate)))
    return results
