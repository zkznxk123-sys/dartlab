"""dartlab flow account 합산 — 단일 진실의 원천.

dartlab finance accessor 의 IS/CIS/CF 컬럼은 분기 단독값
(`pivot.py::_normalizeQ4` 가 raw 4분기 연간을 standalone 으로 변환).
calc 가 연간값을 얻으려면 4분기 합산 필요.

Plan v4 Layer A 이후 `c.IS / c.CIS / c.CF` 는 분기 컬럼 + annual 컬럼
(`{year}`) 둘 다 자동 노출. 따라서 calc 는 보통 `row['2025']` 직접 read.
이 모듈은 분기 부족 종목 / fallback 가 필요한 곳에서만 사용:
- analysis 모드: ttmSum 의 누적공시 fallback (배당금 등 1~2회 이벤트)
- credit 모드: 1~2 분기 부분합산 (부정확하지만 0보다 낫다)

데이터 계약:
- 4 분기 (Q4+Q3+Q2+Q1) 모두 있으면 단순 합 (정확)
- 3 분기 → 평균 × 4 (연환산)
- 1~2 분기 + with_fallback=False → 평균 × 4 (credit 모드, 부정확)
- 1~2 분기 + with_fallback=True → None 또는 누적공시 fallback
- Q1·Q2 None + Q4 단독 → Q4 그대로 (analysis 모드)
"""

from __future__ import annotations

from typing import Iterable


def annualSumFlow(
    flowData: dict,
    qCol: str,
    allPeriods: Iterable[str],
    *,
    withFallback: bool = True,
) -> float | None:
    """Q4 컬럼 기준 그 해 4분기 합산.

    Args:
        flowData: {col: value} 형태. col 은 "YYYYQN" 또는 "YYYY".
        qCol: 기준 컬럼. "Q" 가 없으면 그대로 `flowData.get(qCol)` 반환 (annual mode).
        allPeriods: 사용 가능한 모든 컬럼 (set/list/tuple 모두 OK).
        withFallback: True (analysis 모드) — `ttmSum` 의 누적공시 fallback 적용.
                      False (credit 모드) — 1~2 분기도 부분 합산 후 연환산.

    Returns:
        연간 합산 float, 결손 시 None.

    Examples:
        >>> data = {"2025Q1": 10, "2025Q2": 12, "2025Q3": 14, "2025Q4": 16}
        >>> annualSumFlow(data, "2025Q4", set(data.keys()))
        52.0   # 10 + 12 + 14 + 16

        >>> data = {"2025Q1": None, "2025Q2": None, "2025Q3": None, "2025Q4": 50}
        >>> annualSumFlow(data, "2025Q4", set(data.keys()), withFallback=True)
        50.0   # 누적공시 fallback (배당금 등)
        >>> annualSumFlow(data, "2025Q4", set(data.keys()), withFallback=False)
        200.0   # credit 모드: 50 * 4 (부정확 추정)
    """
    if "Q" not in qCol:
        return flowData.get(qCol)

    year = qCol[:4]
    quarters = [f"{year}Q{q}" for q in (4, 3, 2, 1)]
    periodsSet = set(allPeriods) if not isinstance(allPeriods, set) else allPeriods
    vals = [flowData.get(q) for q in quarters if q in periodsSet]
    valid = [v for v in vals if v is not None]

    if len(valid) >= 3:
        return sum(valid) / len(valid) * 4

    if withFallback:
        # 누적공시 fallback (analysis 모드): Q1·Q2 모두 None + Q4 존재 → Q4 그대로 = 연간 누적
        q4 = flowData.get(f"{year}Q4")
        if q4 is not None:
            q1 = flowData.get(f"{year}Q1")
            q2 = flowData.get(f"{year}Q2")
            if q1 is None and q2 is None:
                return q4
        return None

    # credit 모드: 1~2 분기도 부분 데이터로 연환산 (부정확)
    if valid:
        return sum(valid) / len(valid) * 4
    return None


