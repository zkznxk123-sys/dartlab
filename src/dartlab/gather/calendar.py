"""Calendar capability — 다가오는 catalyst 일정 추론.

Scope (P0):
- 한국 분기/반기/사업보고서 due date 추론 (DART 정기공시 패턴 기반)
- 회사별 disclosure 시계열에서 마지막 정기보고서 → 다음 due 예측
- output schema: date · code · eventType · title · source · impactHint · confidence

Out-of-scope (P1+):
- AGM 일정 disclosure 본문 파싱 (주주총회 안내)
- 회사채 만기 일정
- EDGAR 8-K 미래 일정
- 컨센서스 발표 일정 (FactSet/Bloomberg 필요)

cadence recipe (catalystCalendar.md) 의 데이터 백본.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

import polars as pl

from dartlab.providers.dart import Company

_KR_FILING_TYPES = {
    "사업보고서": ("annual", 90, "ANNUAL_REPORT"),
    "반기보고서": ("semi", 45, "SEMI_REPORT"),
    "분기보고서": ("quarter", 45, "QUARTERLY_REPORT"),
}

_IMPACT_HINTS = {
    "ANNUAL_REPORT": "high — 연간 실적 + 사업 전망 + 감사보고서",
    "SEMI_REPORT": "medium — 반기 실적 + 추세 확인",
    "QUARTERLY_REPORT": "medium — 분기 실적 + 가이던스 변화 가능",
}

_OUTPUT_SCHEMA = {
    "date": pl.Date,
    "code": pl.Utf8,
    "eventType": pl.Utf8,
    "title": pl.Utf8,
    "source": pl.Utf8,
    "impactHint": pl.Utf8,
    "confidence": pl.Utf8,
}


def gatherCalendar(
    codes: str | Iterable[str],
    *,
    horizonDays: int = 30,
    market: str = "KR",
) -> pl.DataFrame:
    """다가오는 catalyst 일정을 추론해 DataFrame 으로 반환.

    Parameters
    ----------
    codes : str | Iterable[str]
        종목코드 1 개 또는 list (예: "005930" 또는 ["005930", "000660"]).
    horizon_days : int
        앞으로 며칠 안의 일정만 반환 (default 30).
    market : str
        "KR" only (US 는 P1 대상). KR 외는 빈 DataFrame + 안내.

    Returns
    -------
    pl.DataFrame
        스키마: date · code · eventType · title · source · impactHint · confidence
        date 기준 오름차순. horizon_days 안의 이벤트만.
        회사별로 다음 정기보고서 1 개씩 추론.

    Notes
    -----
    P0 한계:
    - 한국 정기공시 (사업·반기·분기) 추론만. 컨센서스 발표 / AGM / 만기 미포함.
    - 미국 시장은 빈 결과 + 안내 메시지 (P1 대상).
    - confidence: HIGH (지난 1 년 동일 cycle 보고서 ≥ 2 회 관측), MEDIUM (1 회), LOW (없음 — 추정 보류).
    - 데이터 부족·API 키 미설정 시 빈 DataFrame 반환 (예외 X).

    Example
    -------
    >>> import dartlab
    >>> dartlab.gather("calendar", "005930", horizon_days=60)
    >>> dartlab.gather("calendar", ["005930", "000660"], horizon_days=30)

    Requires
    --------
    DART_API_KEY (Company.disclosure 사용).
    """
    if market != "KR":
        # US/해외 — P1 까지 미지원. 빈 DataFrame + 컬럼 schema 보존.
        return pl.DataFrame(schema=_OUTPUT_SCHEMA)

    code_list = _normalizeCodes(codes)
    if not code_list:
        raise ValueError(
            "gather('calendar') 에는 종목코드가 필요합니다. "
            "예: dartlab.gather('calendar', '005930') 또는 ['005930', '000660']."
        )

    today = date.today()
    horizon_end = today + timedelta(days=horizonDays)
    rows: list[dict] = []

    for code in code_list:
        try:
            company = Company(code)
            history = company.disclosure(days=400, type="A")  # type="A" = 정기공시
        except Exception:
            # 단일 종목 실패는 다른 종목 추론을 막지 않는다.
            continue
        if history is None or history.is_empty():
            continue

        prediction = _predictNextFiling(history, code=code)
        if prediction is None:
            continue
        predicted_date = prediction["date"]
        if not (today <= predicted_date <= horizon_end):
            continue
        rows.append(prediction)

    if not rows:
        return pl.DataFrame(schema=_OUTPUT_SCHEMA)
    return pl.DataFrame(rows, schema=_OUTPUT_SCHEMA).sort("date")


def _normalizeCodes(codes: str | Iterable[str]) -> list[str]:
    if codes is None:
        return []
    if isinstance(codes, str):
        return [codes.strip()] if codes.strip() else []
    return [str(c).strip() for c in codes if str(c).strip()]


def _predictNextFiling(history: pl.DataFrame, *, code: str) -> dict | None:
    """정기공시 시계열에서 다음 due date 추론.

    1. 가장 최근의 사업/반기/분기보고서 식별.
    2. 한국 fiscal calendar 가정 (FY = calendar year) 으로 다음 cycle 의 보고서 type 와 due 계산.
    3. confidence: 같은 type 보고서가 history 에 ≥ 2 회면 HIGH, 1 회면 MEDIUM, 없으면 None.
    """
    if "title" not in history.columns or "filedAt" not in history.columns:
        return None

    # 보고서 type 별 마지막 filedAt 추출
    typeLastDates: dict[str, date] = {}
    type_counts: dict[str, int] = {}
    for row in history.iter_rows(named=True):
        title = row.get("title") or ""
        filed_at = _parseDate(row.get("filedAt"))
        if not filed_at:
            continue
        for kr_name, (cycle_key, _due_offset, eventType) in _KR_FILING_TYPES.items():
            if kr_name in title:
                type_counts[eventType] = type_counts.get(eventType, 0) + 1
                if eventType not in typeLastDates or filed_at > typeLastDates[eventType]:
                    typeLastDates[eventType] = filed_at
                break

    if not typeLastDates:
        return None

    # 다음 보고서 cycle 추론: 한국 정기 보고서는 분기 단위 cycle 이라
    # 가장 가까운 다음 cycle 의 due 를 계산.
    next_event = _nextKrCycle(typeLastDates)
    if next_event is None:
        return None

    eventType, predicted_date = next_event
    count = type_counts.get(eventType, 0)
    if count >= 2:
        confidence = "HIGH"
    elif count == 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    title = _titleForEvent(eventType, predicted_date)
    return {
        "date": predicted_date,
        "code": code,
        "eventType": eventType,
        "title": title,
        "source": f"DART disclosure cycle inference (last {eventType} {typeLastDates[eventType].isoformat()})",
        "impactHint": _IMPACT_HINTS.get(eventType, "medium"),
        "confidence": confidence,
    }


def _nextKrCycle(typeLastDates: dict[str, date]) -> tuple[str, date] | None:
    """한국 정기공시 cycle 다음 due 계산.

    한국 fiscal year = calendar year 가정 (대다수 상장사):
    - Q1 분기보고서 (Jan-Mar 결산) due ~5 월 15 일
    - Q2 반기보고서 (Apr-Jun 결산) due ~8 월 14 일
    - Q3 분기보고서 (Jul-Sep 결산) due ~11 월 14 일
    - 사업보고서 (Q4 + 연간 결산) due ~3 월 31 일 (다음 해)

    오늘 시점 기준으로 다가오는 가장 가까운 cycle event 를 선택.
    """
    today = date.today()
    year = today.year
    candidates: list[tuple[str, date]] = [
        ("QUARTERLY_REPORT", date(year, 5, 15)),
        ("SEMI_REPORT", date(year, 8, 14)),
        ("QUARTERLY_REPORT", date(year, 11, 14)),
        ("ANNUAL_REPORT", date(year + 1, 3, 31)),
        # 다음 해 첫 분기도 horizon 60+ 일 케이스 위해
        ("QUARTERLY_REPORT", date(year + 1, 5, 15)),
    ]
    upcoming = [(et, d) for et, d in candidates if d >= today]
    if not upcoming:
        return None

    # 가장 가까운 cycle. 단 history 에 그 type 보고서가 한 번이라도 있어야 추론.
    for eventType, predicted in upcoming:
        if eventType in typeLastDates:
            # 마지막 보고서가 너무 오래된 (1 년 이상) 경우 skip — 회사가 비활성/폐지 가능
            last = typeLastDates[eventType]
            if (today - last).days > 400:
                continue
            return eventType, predicted
    return None


def _parseDate(value) -> date | None:
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
    if eventType == "ANNUAL_REPORT":
        return f"사업보고서 제출 예상 (FY{predicted.year - 1})"
    if eventType == "SEMI_REPORT":
        return f"반기보고서 제출 예상 ({predicted.year} H1)"
    if eventType == "QUARTERLY_REPORT":
        # 5 월 15 일 → Q1, 11 월 14 일 → Q3
        if predicted.month <= 6:
            return f"분기보고서 제출 예상 ({predicted.year} Q1)"
        return f"분기보고서 제출 예상 ({predicted.year} Q3)"
    return f"{eventType} 제출 예상"
