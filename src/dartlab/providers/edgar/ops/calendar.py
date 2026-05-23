"""SEC Filing Calendar — 10-K / 10-Q / 8-K 다음 due date 예측.

SEC 의 정기 filing cadence (회계연도 종료 후 60/90 일) 기반 통계적 예측.
dart/ops/calendar 의 US 등가 — KR fiscal cycle (3/5/8/11) 대신 fiscal year
end + standard SEC deadline 사용.

핵심 SEC deadline (Reg S-X):
- 10-K (annual): fiscal year end + 60 일 (large accelerated filer) / 75 일 (accelerated)
  / 90 일 (non-accelerated). default 75 일.
- 10-Q (quarterly): fiscal quarter end + 40 일 (large/accelerated) / 45 일
  (non-accelerated). default 40 일.

본 wrapper 는 thin — recent SEC filing history (Company.disclosure 등가)
입력 → 다음 due date 예측 DataFrame 반환.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

OUTPUT_SCHEMA: dict[str, pl.DataType] = {
    "date": pl.Date,
    "cik": pl.Utf8,
    "eventType": pl.Utf8,
    "title": pl.Utf8,
    "source": pl.Utf8,
    "impactHint": pl.Utf8,
    "confidence": pl.Utf8,
}

# SEC standard filing deadlines (days after period end).
_DEADLINE_DAYS = {
    "10-K": 75,
    "10-Q": 40,
}

_EVENT_TITLE = {
    "10-K": "10-K Annual Report",
    "10-Q": "10-Q Quarterly Report",
}


def predictCalendar(
    disclosures: dict[str, pl.DataFrame],
    *,
    horizonDays: int = 30,
) -> pl.DataFrame:
    """다가오는 SEC 정기 filing catalyst 일정 추론.

    회사별 filing history 의 최근 ``10-K`` / ``10-Q`` 등장 패턴에서 SEC deadline
    (10-K 75 일, 10-Q 40 일) 적용 → 다음 due date 예측.

    Args:
        disclosures: ``{cik: filingHistory}`` 매핑. history 는 최소 ``formType``
            (예 ``"10-K"``) + ``fileDate`` (접수일 date) 컬럼 보유.
        horizonDays: today 부터 며칠 안의 일정만 반환. default 30. 7~120 권장.

    Returns:
        pl.DataFrame — schema ``OUTPUT_SCHEMA``. row 가 다음 catalyst 1 개씩.
        disclosures 가 빈 dict 면 빈 DataFrame (schema 보존).

    Raises:
        없음 — schema 불일치는 해당 cik skip.

    Example:
        >>> import polars as pl
        >>> from datetime import date
        >>> hist = pl.DataFrame({
        ...     "formType": ["10-K", "10-Q"],
        ...     "fileDate": [date(2024, 2, 1), date(2024, 5, 1)],
        ... })
        >>> df = predictCalendar({"0000320193": hist}, horizonDays=400)
        >>> df.shape[0] >= 0
        True
    """
    if not disclosures:
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    today = date.today()
    horizonEnd = today + timedelta(days=horizonDays)

    rows: list[dict[str, object]] = []
    for cik, history in disclosures.items():
        if history is None or history.is_empty():
            continue
        if "formType" not in history.columns or "fileDate" not in history.columns:
            continue
        predicted = _predictNextFiling(history, cik=cik, today=today)
        if not predicted:
            continue
        if predicted["date"] > horizonEnd:
            continue
        rows.append(predicted)

    if not rows:
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    return pl.DataFrame(rows, schema=OUTPUT_SCHEMA).sort("date")


def _predictNextFiling(history: pl.DataFrame, *, cik: str, today: date) -> dict | None:
    """단일 회사의 마지막 정기 filing 에서 다음 due date 예측.

    Args:
        history: ``formType`` + ``fileDate`` 컬럼 보유 DataFrame.
        cik: 회사 CIK.
        today: 비교 기준 today.

    Returns:
        ``OUTPUT_SCHEMA`` 형식의 dict 또는 매칭 부재 시 None.

    Raises:
        없음.

    Example:
        >>> _predictNextFiling(history, cik="0000320193", today=date.today())  # doctest: +SKIP
    """
    # 10-K / 10-Q 만 필터.
    filtered = history.filter(pl.col("formType").is_in(list(_DEADLINE_DAYS.keys())))
    if filtered.is_empty():
        return None
    # formType 별 마지막 filing.
    lastByForm: dict[str, date] = {}
    for row in filtered.iter_rows(named=True):
        formType = str(row.get("formType") or "")
        fileDate = row.get("fileDate")
        if not isinstance(fileDate, date):
            continue
        prev = lastByForm.get(formType)
        if prev is None or fileDate > prev:
            lastByForm[formType] = fileDate

    # 다음 due date 후보 — formType 별 (lastFile + cycle days).
    candidates: list[tuple[date, str, str]] = []
    for formType, lastDate in lastByForm.items():
        deadlineDays = _DEADLINE_DAYS[formType]
        # 10-K = 1 년 cycle, 10-Q = 1 분기 (~91 일) cycle.
        cycleDays = 365 if formType == "10-K" else 91
        # 마지막 filing 의 *fiscal period end* 는 fileDate - deadlineDays.
        # 다음 period end = fileDate - deadlineDays + cycleDays.
        nextPeriodEnd = lastDate - timedelta(days=deadlineDays) + timedelta(days=cycleDays)
        nextDue = nextPeriodEnd + timedelta(days=deadlineDays)
        # 이미 지나간 예측 — today 까지 cycle 반복 추가.
        while nextDue < today:
            nextDue = nextDue + timedelta(days=cycleDays)
        candidates.append((nextDue, formType, _EVENT_TITLE[formType]))

    if not candidates:
        return None
    # 가장 가까운 due date.
    candidates.sort()
    nextDue, formType, title = candidates[0]
    confidence = "HIGH" if filtered.filter(pl.col("formType") == formType).height >= 2 else "MEDIUM"
    impactHint = "high" if formType == "10-K" else "medium"
    return {
        "date": nextDue,
        "cik": cik,
        "eventType": formType,
        "title": title,
        "source": f"last {formType}: {lastByForm[formType]} + {_DEADLINE_DAYS[formType]}d SEC deadline",
        "impactHint": impactHint,
        "confidence": confidence,
    }
