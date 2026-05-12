"""DART 정기공시 catalyst 일정 추론 — Company.calendar() 본체.

이전 위치: gather/calendar.py (gather → providers cycle 의 한 축).
새 위치: providers/dart 안 — KR 정기공시 (DART 전용) 도메인 적합. providers 가 자체 calendar
추론을 책임지고 gather 가 providers 호출 안 함 (단방향).

Scope (P0):
- 한국 분기/반기/사업보고서 due date 추론 (DART 정기공시 패턴 기반)
- 회사별 disclosure 시계열에서 마지막 정기보고서 → 다음 due 예측
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import polars as pl

KR_FILING_TYPES = {
    "사업보고서": ("annual", 90, "ANNUAL_REPORT"),
    "반기보고서": ("semi", 45, "SEMI_REPORT"),
    "분기보고서": ("quarter", 45, "QUARTERLY_REPORT"),
}

IMPACT_HINTS = {
    "ANNUAL_REPORT": "high — 연간 실적 + 사업 전망 + 감사보고서",
    "SEMI_REPORT": "medium — 반기 실적 + 추세 확인",
    "QUARTERLY_REPORT": "medium — 분기 실적 + 가이던스 변화 가능",
}

OUTPUT_SCHEMA = {
    "date": pl.Date,
    "code": pl.Utf8,
    "eventType": pl.Utf8,
    "title": pl.Utf8,
    "source": pl.Utf8,
    "impactHint": pl.Utf8,
    "confidence": pl.Utf8,
}


def predictCalendar(
    disclosures: dict[str, pl.DataFrame],
    *,
    horizonDays: int = 30,
) -> pl.DataFrame:
    """다가오는 KR 정기공시 catalyst 일정 추론.

    Capabilities:
        - 회사별 disclosure history 에서 마지막 정기보고서를 식별하고 KR fiscal cycle
          (사업 ~3/31, 분기 ~5/15·~11/14, 반기 ~8/14) 으로 다음 due date 예측.
        - 동일 type 보고서가 history 에 2 회 이상이면 HIGH confidence, 1 회면 MEDIUM.
        - horizon (default 30 일) 범위 밖 예측은 제외.

    Args:
        disclosures: ``{stockCode: disclosureHistory}`` 매핑. history 는 최소
            ``title`` (보고서 한글 제목) 과 ``filedAt`` (접수일) 컬럼 보유. caller 가
            ``c.disclosure(type="A")`` 같은 정기공시 history 를 미리 수집해 전달.
        horizonDays: today 부터 며칠 안의 일정만 반환. default 30. 7~120 권장.

    Returns:
        pl.DataFrame — 스키마 ``OUTPUT_SCHEMA``: ``date`` (예측일) · ``code`` (종목코드)
        · ``eventType`` (ANNUAL_REPORT/SEMI_REPORT/QUARTERLY_REPORT) · ``title`` (한글 제목)
        · ``source`` (추론 근거) · ``impactHint`` (high/medium 영향) · ``confidence``
        (HIGH/MEDIUM/LOW). disclosures 가 비어있으면 빈 DataFrame (스키마만 보존).

    Example:
        >>> import polars as pl
        >>> from datetime import date
        >>> hist = pl.DataFrame({
        ...     "title": ["사업보고서 (2024.12)", "사업보고서 (2023.12)"],
        ...     "filedAt": [date(2025, 3, 28), date(2024, 3, 27)],
        ... })
        >>> df = predictCalendar({"005930": hist}, horizonDays=400)
        >>> df.shape[0] >= 0  # 다음 ANNUAL_REPORT 예측 (현 today 와 horizon 에 따라)
        True

    Guide:
        - "삼성전자 다음 catalyst 언제?" → ``predictCalendar({"005930": history}, horizonDays=90)``
        - "다가오는 분기보고서 일정" → 결과 ``df.filter(pl.col("eventType")=="QUARTERLY_REPORT")``
        - 여러 종목 동시 → disclosures dict 에 stockCode 별 history 묶어 1 회 호출.

    SeeAlso:
        - ``dartlab.providers.dart.Company.disclosure`` — 본 함수가 받는 history 의 출처.
        - ``KR_FILING_TYPES`` / ``OUTPUT_SCHEMA`` — 모듈 상수, 분류 + 반환 스키마.
        - ``_predictNextFiling`` — 종목 1 개에 대한 단일 예측 로직.

    Requires:
        - polars — DataFrame 입출력.
        - datetime — date/timedelta 으로 fiscal cycle 계산.
        - 외부 API 없음 — disclosure history 만으로 추론.

    AIContext:
        Ask Workbench 의 timing/catalyst 토픽 추론 시 호출. history 가 부재하면 빈
        DataFrame 반환이므로 caller 는 결과 empty check + fallback (예 "다음 catalyst
        정보 부족") 필요. confidence=LOW 결과는 evidence 로 인용 시 신뢰도 명시.

    LLM Specifications:
        AntiPatterns:
            - disclosures dict 의 history 에 ``title``/``filedAt`` 컬럼 부재 → 본 함수가
              해당 종목 skip (전체 fail 아님). 호출자가 schema 검증 의무 없음.
            - horizonDays 0 또는 음수 → 빈 DataFrame (예측 없음).
            - history 의 filedAt 가 ISO 외 형식 (예 "2024년 3월 31일") → ``_parseDate``
              가 fallback 시도, 실패 시 해당 row skip.
        OutputSchema:
            - row: 1 종목당 다음 catalyst 1 개 (가장 가까운 due).
            - column: ``date`` (pl.Date) / ``code`` (pl.Utf8) / ``eventType`` (pl.Utf8)
              / ``title`` (pl.Utf8) / ``source`` (pl.Utf8) / ``impactHint`` (pl.Utf8)
              / ``confidence`` (pl.Utf8).
            - 정렬: ``date`` 오름차순 (가장 가까운 일정 먼저).
        Prerequisites:
            - caller 가 stockCode → disclosure history (type="A") 사전 수집.
            - 정기공시 외 type (Z/I 등) history 는 분류 패턴 미매칭 → skip.
        Freshness:
            - 외부 API 미사용. history 가 freshness 결정 — caller 책임.
            - KR fiscal cycle 가정 (대다수 상장사 calendar year). 12월 결산 외 회사는
              부정확.
        Dataflow:
            - caller (``Company.disclosure`` / ``c.calendar()``) → 본 함수 → DataFrame.
        TargetMarkets:
            - KR (DART). EDGAR/EDINET 은 별도 fiscal cycle — 본 함수 미지원.

    Raises:
        없음.
    """
    if not disclosures:
        return pl.DataFrame(schema=OUTPUT_SCHEMA)

    today = date.today()
    horizonEnd = today + timedelta(days=horizonDays)
    rows: list[dict] = []

    for code, history in disclosures.items():
        if history is None or history.is_empty():
            continue
        prediction = _predictNextFiling(history, code=code)
        if prediction is None:
            continue
        if not (today <= prediction["date"] <= horizonEnd):
            continue
        rows.append(prediction)

    if not rows:
        return pl.DataFrame(schema=OUTPUT_SCHEMA)
    return pl.DataFrame(rows, schema=OUTPUT_SCHEMA).sort("date")


def _predictNextFiling(history: pl.DataFrame, *, code: str) -> dict | None:
    """정기공시 시계열에서 다음 due date 추론.

    1. 가장 최근의 사업/반기/분기보고서 식별.
    2. 한국 fiscal calendar 가정 (FY = calendar year) 으로 다음 cycle 의 보고서 type 와 due 계산.
    3. confidence: 같은 type 보고서가 history 에 ≥ 2 회면 HIGH, 1 회면 MEDIUM, 없으면 None.
    """
    if "title" not in history.columns or "filedAt" not in history.columns:
        return None

    typeLastDates: dict[str, date] = {}
    typeCounts: dict[str, int] = {}
    for row in history.iter_rows(named=True):
        title = row.get("title") or ""
        filedAt = _parseDate(row.get("filedAt"))
        if not filedAt:
            continue
        for krName, (_cycleKey, _dueOffset, eventType) in KR_FILING_TYPES.items():
            if krName in title:
                typeCounts[eventType] = typeCounts.get(eventType, 0) + 1
                if eventType not in typeLastDates or filedAt > typeLastDates[eventType]:
                    typeLastDates[eventType] = filedAt
                break

    if not typeLastDates:
        return None

    nextEvent = _nextKrCycle(typeLastDates)
    if nextEvent is None:
        return None

    eventType, predictedDate = nextEvent
    count = typeCounts.get(eventType, 0)
    if count >= 2:
        confidence = "HIGH"
    elif count == 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    title = _titleForEvent(eventType, predictedDate)
    return {
        "date": predictedDate,
        "code": code,
        "eventType": eventType,
        "title": title,
        "source": f"DART disclosure cycle inference (last {eventType} {typeLastDates[eventType].isoformat()})",
        "impactHint": IMPACT_HINTS.get(eventType, "medium"),
        "confidence": confidence,
    }


def _nextKrCycle(typeLastDates: dict[str, date]) -> tuple[str, date] | None:
    """한국 정기공시 cycle 다음 due 계산.

    한국 fiscal year = calendar year 가정 (대다수 상장사):
    - Q1 분기보고서 due ~5/15, 반기 ~8/14, Q3 ~11/14, 사업 ~3/31 (다음해)
    """
    today = date.today()
    year = today.year
    candidates: list[tuple[str, date]] = [
        ("QUARTERLY_REPORT", date(year, 5, 15)),
        ("SEMI_REPORT", date(year, 8, 14)),
        ("QUARTERLY_REPORT", date(year, 11, 14)),
        ("ANNUAL_REPORT", date(year + 1, 3, 31)),
        ("QUARTERLY_REPORT", date(year + 1, 5, 15)),
    ]
    upcoming = [(et, d) for et, d in candidates if d >= today]
    if not upcoming:
        return None

    for eventType, predicted in upcoming:
        if eventType in typeLastDates:
            last = typeLastDates[eventType]
            if (today - last).days > 400:
                continue
            return eventType, predicted
    return None


def _parseDate(value) -> date | None:
    """다양한 형식 (date/datetime/str) 의 입력을 date 로 변환. 실패 시 None."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _titleForEvent(eventType: str, predicted: date) -> str:
    """eventType + 예상일 → 한국어 제목."""
    if eventType == "ANNUAL_REPORT":
        return f"사업보고서 제출 예상 (FY{predicted.year - 1})"
    if eventType == "SEMI_REPORT":
        return f"반기보고서 제출 예상 ({predicted.year} H1)"
    if eventType == "QUARTERLY_REPORT":
        if predicted.month <= 6:
            return f"분기보고서 제출 예상 ({predicted.year} Q1)"
        return f"분기보고서 제출 예상 ({predicted.year} Q3)"
    return f"{eventType} 제출 예상"
