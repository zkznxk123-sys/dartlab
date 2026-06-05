"""EDGAR panel compare facade — DART compare surface for US tickers."""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.panel.compare import compare as _compare


def compare(
    codes: list[str] | str,
    *,
    topic: str | None = None,
    period: list[str] | str | None = None,
    scope: str | None = None,
    freq: str = "quarter",
) -> pl.DataFrame:
    """N개 EDGAR ticker panel 을 DART compare 계약으로 비교한다.

    Args:
        codes: US ticker 하나 또는 ticker 목록.
        topic: 비교할 statement/topic.
        period: 선택 기간 또는 기간 목록.
        scope: 선택 scope.
        freq: ``"quarter"`` 또는 ``"annual"``.

    Returns:
        ticker 간 비교 wide DataFrame.

    Raises:
        ValueError: 하위 DART compare 계약에서 입력/데이터가 유효하지 않을 때.

    Example:
        >>> compare(["AAPL", "MSFT"], topic="is")  # doctest: +SKIP
    """
    return _compare(codes, topic=topic, period=period, scope=scope, freq=freq)


__all__ = ["compare"]
