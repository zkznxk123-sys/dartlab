"""Polars DataFrame 공통 유틸리티.

`df is None or df.is_empty()` 패턴 99회 중복 제거를 위한 SSoT.
"""

from __future__ import annotations

from typing import Any


def isValidDf(df: Any) -> bool:
    """DataFrame 이 None 이 아니고 비어있지 않으면 True.

    기존 ``df is None or df.is_empty()`` 패턴의 부정 형태 (즉 ``not isValidDf(df)``
    가 기존 표현과 동치). 가독성을 위해 긍정형 이름 사용.

    Examples:
        >>> import polars as pl
        >>> isValidDf(None)
        False
        >>> isValidDf(pl.DataFrame())
        False
        >>> isValidDf(pl.DataFrame({"a": [1]}))
        True
    """
    if df is None:
        return False
    # polars.DataFrame.is_empty() 는 height == 0 체크. LazyFrame 은 collect 필요하므로
    # width 만 확인 (LazyFrame.is_empty 는 존재하지 않음, collect 후 체크가 맞음).
    isEmpty = getattr(df, "is_empty", None)
    if callable(isEmpty):
        return not isEmpty()
    return True


def isEmptyDf(df: Any) -> bool:
    """DataFrame 이 None 이거나 비어있으면 True (기존 패턴 직접 형태)."""
    return not isValidDf(df)
