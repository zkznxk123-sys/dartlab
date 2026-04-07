"""dartlab flow account 합산 — 단일 진실의 원천.

dartlab finance accessor 의 IS/CIS/CF 컬럼은 분기 단독값
(`pivot.py::_normalizeQ4` 가 raw 4분기 연간을 standalone 으로 변환).
calc/narrative 가 연간값을 얻으려면 4분기 합산 필요.

기존 분산 헬퍼 (모두 다른 시그니처/fallback):
- `analysis/financial/_helpers.py::ttmSum`         (set, with_fallback, minQ=3)
- `analysis/financial/_helpers.py::getFlowValue`    (boolean wrapper)
- `credit/metrics.py::_ttmSum`                     (list, no fallback, 1+ Q OK)
- `review/narrative.py::_annualizeFlow`            (dict[str,dict] wrapper)

이 모듈이 단일 표준 + 옵션 인자. 4 헬퍼 모두 위임.

데이터 계약:
- 4 분기 (Q4+Q3+Q2+Q1) 모두 있으면 단순 합 (정확)
- 3 분기 → 평균 × 4 (연환산)
- 1~2 분기 + with_fallback=False → 평균 × 4 (credit 모드, 부정확)
- 1~2 분기 + with_fallback=True → None 또는 누적공시 fallback
- Q1·Q2 None + Q4 단독 → Q4 그대로 (배당금/자사주 같은 1~2회 이벤트, ttmSum 모드)
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


def annualizeFlowRows(rows: dict[str, dict], periods: list[str]) -> dict[str, dict]:
    """flow rows dict 의 Q4 컬럼을 그 해 연간 합으로 교체.

    Plan v4 Layer A 후 dartlab `c.IS / c.CIS / c.CF` 는 이미 annual 컬럼 (`{year}`)
    을 노출하므로 detector 가 `_annualCols` 로 4자리 연도 우선 잡고 그것을 직접
    read 하면 됨. 이 함수는 사용처 0 (deprecated).

    호환 유지를 위해 함수 자체는 보존. 새 코드는 사용 금지.
    """
    if not rows or not periods:
        return rows
    years: set[str] = set()
    for p in periods:
        if "Q" in p and len(p) >= 5:
            years.add(p[:4])
    if not years:
        return rows

    periodsSet = set(periods)
    out: dict[str, dict] = {}
    for name, row in rows.items():
        if not row:
            out[name] = row
            continue
        newRow = dict(row)
        for year in years:
            qCol = f"{year}Q4"
            v = annualSumFlow(row, qCol, periodsSet, withFallback=True)
            if v is not None:
                newRow[qCol] = v
        out[name] = newRow
    return out
