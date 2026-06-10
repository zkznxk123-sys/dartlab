"""관세청 월별 수출입 시계열 빌드 — 윈도 분할 + 국가총계 월별 합산.

API 는 1년 윈도·하위HS·국가 분해로 응답한다. 본 레이어가 (1) 1년 이내로 분할
호출, (2) ``year=총계`` 요약행 제외, (3) ``year`` 월별로 metric 합산해 국가총계
월별 (date, value) 시계열로 환원한다. FRED/ECOS ``series`` 와 동일 반환 계약.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from .client import CustomsClient

_VALID_METRICS = ("expDlr", "impDlr", "balPayments")
_EMPTY = pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})


def _normalizeYm(value: str) -> str:
    """'YYYY-MM' / 'YYYYMM' / 'YYYY-MM-DD' → 'YYYYMM'."""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[:6]


def _ymToIndex(ym: str) -> int:
    return int(ym[:4]) * 12 + (int(ym[4:6]) - 1)


def _indexToYm(idx: int) -> str:
    return f"{idx // 12:04d}{idx % 12 + 1:02d}"


def _monthWindows(startYm: str, endYm: str, *, maxMonths: int = 12) -> list[tuple[str, str]]:
    """[startYm, endYm] 을 maxMonths 이내 (strt, end) 윈도로 분할."""
    s, e = _ymToIndex(startYm), _ymToIndex(endYm)
    if s > e:
        return []
    windows: list[tuple[str, str]] = []
    cur = s
    while cur <= e:
        last = min(cur + maxMonths - 1, e)
        windows.append((_indexToYm(cur), _indexToYm(last)))
        cur = last + 1
    return windows


def _parseMonth(year: str) -> dt.date | None:
    """'2025.10' → date(2025,10,1). '총계'/이상값 → None."""
    parts = year.replace("-", ".").split(".")
    if len(parts) != 2:
        return None
    try:
        return dt.date(int(parts[0]), int(parts[1]), 1)
    except (ValueError, TypeError):
        return None


def _aggregateMonthly(items: list[dict[str, str]], metric: str) -> dict[dt.date, float]:
    """item 행들 → 월별 metric 합산 (총계행·비월 행 제외)."""
    out: dict[dt.date, float] = {}
    for row in items:
        month = _parseMonth(row.get("year", ""))
        if month is None:
            continue
        try:
            val = float(row.get(metric, "0") or "0")
        except ValueError:
            continue
        out[month] = out.get(month, 0.0) + val
    return out


def fetchSeries(
    client: CustomsClient,
    hsCode: str,
    *,
    start: str | None = None,
    end: str | None = None,
    metric: str = "expDlr",
) -> pl.DataFrame:
    """HS 품목의 월별 국가총계 수출입 시계열.

    Capabilities: 윈도 분할 호출 + 월별 합산 → (date, value). metric 선택으로
        수출액/수입액/무역수지 중 하나를 value 로.

    Args:
        client: CustomsClient.
        hsCode: HS 코드 (2/4/6자리).
        start: 시작 'YYYY-MM'/'YYYYMM'. None 이면 ``"200001"``.
        end: 종료. None 이면 현재 월.
        metric: ``"expDlr"``(수출 USD, 기본) | ``"impDlr"`` | ``"balPayments"``.

    Returns:
        pl.DataFrame — date(Date, 월초)·value(Float64). 빈 결과는 빈 스키마.

    Raises:
        ValueError: metric 이 expDlr/impDlr/balPayments 외.
        CustomsError: API 오류 (client 경유).

    Example:
        >>> df = fetchSeries(client, "8542", start="2025-01")  # doctest: +SKIP
    """
    if metric not in _VALID_METRICS:
        raise ValueError(f"metric 은 {_VALID_METRICS} 중 하나여야 합니다: {metric!r}")
    startYm = _normalizeYm(start) if start else "200001"
    endYm = _normalizeYm(end) if end else dt.date.today().strftime("%Y%m")

    merged: dict[dt.date, float] = {}
    for wStart, wEnd in _monthWindows(startYm, endYm):
        items = client.get(hsCode, wStart, wEnd)
        for month, val in _aggregateMonthly(items, metric).items():
            merged[month] = merged.get(month, 0.0) + val
    if not merged:
        return _EMPTY.clone()
    rows = sorted(merged.items())
    return pl.DataFrame(
        {"date": [m for m, _ in rows], "value": [v for _, v in rows]},
        schema={"date": pl.Date, "value": pl.Float64},
    )
