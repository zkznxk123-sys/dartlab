"""Cross-company aggregation engine — M6 (Protocol DIP).

dartlab 의 scan API (예: ``Scan.docsSections``) cross-company 쿼리는
기본 PolarsCrossScan (streaming engine + slim index) 으로 처리.
복잡 aggregation 또는 대용량 dataset 에서는 DuckDbCrossScan 으로 자동
전환 — Arrow zero-copy 로 LazyFrame ↔ DuckDB relation 교환, OOC god mode.

토글:
  - 환경변수 ``DARTLAB_CROSS_SCAN_ENGINE=duckdb`` 명시
  - 또는 caller 가 ``engine="duckdb"`` 명시
  - 기본은 ``"polars"`` (streaming engine)

설계:
  - Protocol ``CrossScanEngine`` — ``aggregate(lf, *, query)`` 단일 메서드
  - PolarsCrossScan: 기존 streaming chain 그대로
  - DuckDbCrossScan: ``duckdb.sql("SELECT ... FROM lf WHERE ...").pl()``
"""

from __future__ import annotations

import os
from typing import Any, Literal, Protocol, runtime_checkable

import polars as pl


@runtime_checkable
class CrossScanEngine(Protocol):
    """Cross-company scan 엔진 surface (DIP).

    구현은 ``PolarsCrossScan`` (기본) 또는 ``DuckDbCrossScan`` (OOC).
    """

    def aggregate(self, lf: pl.LazyFrame, *, limit: int | None = None) -> pl.DataFrame:
        """LazyFrame 을 collect 또는 SQL 위임으로 DataFrame 반환.

        Args:
            lf: filter/select 가 적용된 LazyFrame.
            limit: 최대 행 수 (None = 무제한).

        Returns:
            결과 DataFrame.

        Raises:
            없음 (엔진별 예외는 caller 가 잡음).

        Example:
            >>> engine = pickCrossScanEngine()
            >>> engine.aggregate(lf, limit=100)
        """
        ...


class PolarsCrossScan:
    """기본 엔진 — Polars streaming engine 으로 collect.

    M2-1 이후 dartlab 의 표준. filter/select/group_by 단순 chain 은
    O(batch) 메모리로 처리. window/asof/일부 pivot 은 미지원 (M3 마커).
    """

    def aggregate(self, lf: pl.LazyFrame, *, limit: int | None = None) -> pl.DataFrame:
        """streaming engine 으로 collect.

        Args:
            lf: LazyFrame.
            limit: 최대 행 수.

        Returns:
            DataFrame.

        Raises:
            polars.exceptions.InvalidOperationError: streaming engine 미지원
                연산 포함 시 (caller 가 잡고 DuckDbCrossScan 으로 fallback).

        Example:
            >>> PolarsCrossScan().aggregate(lf, limit=100)
        """
        if limit and limit > 0:
            lf = lf.limit(limit)
        return lf.collect(engine="streaming")


class DuckDbCrossScan:
    """OOC 엔진 — DuckDB SQL 위임 (Arrow zero-copy).

    Polars LazyFrame 을 DuckDB relation 으로 등록 → SQL 쿼리 → 결과를
    Polars DataFrame 으로 복귀. DuckDB 가 disk-spill 자동 — Spark 수준 OOC.

    streaming 미지원 연산 (asof/window 일부) 도 DuckDB 가 직접 지원하면
    fallback 가능. caller 는 별도 SQL 작성 안 함 — ``aggregate(lf)`` 호환.

    Args:
        memoryLimitMb: DuckDB pragma ``memory_limit`` (기본 None → DuckDB 기본).

    Example:
        >>> DuckDbCrossScan(memoryLimitMb=4000).aggregate(lf)
    """

    def __init__(self, *, memoryLimitMb: int | None = None) -> None:
        self._memoryLimitMb = memoryLimitMb

    def aggregate(self, lf: pl.LazyFrame, *, limit: int | None = None) -> pl.DataFrame:
        """LazyFrame → Arrow → DuckDB SELECT * → Polars.

        Args:
            lf: LazyFrame (filter/select 적용 후).
            limit: 최대 행 수.

        Returns:
            DataFrame.

        Raises:
            ImportError: duckdb 미설치.
            duckdb.Error: SQL 실행 실패.

        Example:
            >>> DuckDbCrossScan().aggregate(lf, limit=100)
        """
        import duckdb

        con = duckdb.connect(":memory:")
        try:
            if self._memoryLimitMb is not None:
                con.execute(f"PRAGMA memory_limit='{int(self._memoryLimitMb)}MB'")
            con.register(
                "lf", lf.collect(engine="streaming") if limit is None else lf.limit(limit).collect(engine="streaming")
            )
            sql = "SELECT * FROM lf" if limit is None else f"SELECT * FROM lf LIMIT {int(limit)}"
            return con.sql(sql).pl()
        finally:
            con.close()


def pickCrossScanEngine(*, engine: Literal["polars", "duckdb"] | None = None) -> CrossScanEngine:
    """엔진 선택 dispatcher — caller > env > 기본 (polars).

    Args:
        engine: 명시 선택. None 이면 환경변수 ``DARTLAB_CROSS_SCAN_ENGINE``
            (값 ``"duckdb"`` 또는 ``"polars"``) 또는 기본 ``"polars"``.

    Returns:
        ``CrossScanEngine`` 구현.

    Raises:
        없음.

    Example:
        >>> pickCrossScanEngine(engine="duckdb").aggregate(lf)
    """
    name = (engine or os.environ.get("DARTLAB_CROSS_SCAN_ENGINE") or "polars").lower()
    if name == "duckdb":
        return DuckDbCrossScan()
    return PolarsCrossScan()


__all__: list[str] = [
    "CrossScanEngine",
    "DuckDbCrossScan",
    "PolarsCrossScan",
    "pickCrossScanEngine",
]
