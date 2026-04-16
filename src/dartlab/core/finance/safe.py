"""안전 헬퍼 SSOT — 11 파일 중복 제거 (Phase 16 B1).

기존 분산:
- `_get(row, col)` 11 파일 중복 정의 (100% 복붙)
- `_getF / _getF2 / _getF3 / _getF4` 이름만 다르게 7 파일
- `_getFirst(data, keys, col)` 3 파일
- `_yoy(cur, prev)` 3 파일

→ 본 모듈로 SSOT 통합. import 경로:
    from dartlab.core.finance.safe import get, getFirst, yoy

버그 수정 시 1곳만 수정 (기존: 42곳).
"""

from __future__ import annotations


def get(row: dict | None, col: str, default: float = 0) -> float:
    """dict row 에서 값 안전 추출. None/missing → default.

    Args:
        row: 소스 dict (None 가능).
        col: 조회 key.
        default: 없을 때 반환값 (기본 0).

    Returns:
        row[col] 이 None 아니면 그 값, 아니면 default.

    Examples:
        >>> get({"2024": 100}, "2024")
        100
        >>> get({"2024": None}, "2024")
        0
        >>> get(None, "2024")
        0
        >>> get({}, "missing", default=-1)
        -1
    """
    if row is None:
        return default
    v = row.get(col)
    return v if v is not None else default


def getFirst(data: dict, keys: list[str], col: str, default: float = 0) -> float:
    """여러 key 후보 중 첫 유효값 반환.

    Args:
        data: 중첩 dict {key: {col: value}}.
        keys: 순서대로 시도할 key 리스트.
        col: 각 row 의 조회 컬럼.
        default: 모두 실패 시 반환.

    Returns:
        유효한 첫 값 (None/0 이 아닌). 없으면 default.

    Examples:
        >>> data = {"매출액": {"2024": 1000}, "매출": {"2024": None}}
        >>> getFirst(data, ["매출", "매출액"], "2024")
        1000
    """
    for k in keys:
        row = data.get(k)
        if not row:
            continue
        v = row.get(col)
        if v is not None and v != 0:
            return v
    return default


def yoy(cur: float | None, prev: float | None) -> float | None:
    """YoY 변화율 (%) 계산. None/0 안전.

    Args:
        cur: 현재 값.
        prev: 이전 값.

    Returns:
        (cur - prev) / |prev| * 100. prev=0 또는 None 이면 None.

    Examples:
        >>> yoy(110, 100)
        10.0
        >>> yoy(90, 100)
        -10.0
        >>> yoy(100, 0) is None
        True
    """
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 2)
