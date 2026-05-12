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

        Capabilities:
            - LazyFrame → DataFrame 변환의 통일 surface. polars streaming / duckdb 두 구현이
              같은 시그니처라 caller 무중단 swap.

        Guide:
            -

        When:
            호출 컨텍스트.

        How:
            구현.

        AIContext:
            cross-company aggregation 이 메모리 압박 환경에서도 안전하게 돌도록 caller 가
            엔진 선택 logic 없이 ``pickCrossScanEngine().aggregate(lf)`` 한 번에 처리.

        Requires:
            - LazyFrame (filter/select 적용 후)

        SeeAlso:
            - :class:`PolarsCrossScan` · :class:`DuckDbCrossScan` — 두 구현
            - :func:`pickCrossScanEngine` — dispatcher
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

        Capabilities:
            - polars streaming engine 으로 LazyFrame collect. M2-1 이후 dartlab 의 표준 (filter/
              select/group_by 단순 chain 은 O(batch) 메모리).

        Guide:
            -

        When:
            호출 컨텍스트.

        How:
            구현.

        AIContext:
            기본 cross-scan 엔진. 미지원 연산 (asof/window 일부) 만나면 caller 가 catch 후
            ``DuckDbCrossScan`` 으로 fallback.

        Requires:
            - polars (필수, 표준 의존)

        SeeAlso:
            - :class:`DuckDbCrossScan` — streaming 미지원 연산 fallback
            - :func:`pickCrossScanEngine`
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

        Capabilities:
            - polars LazyFrame → DuckDB relation 등록 → SQL SELECT → polars DataFrame 복귀
              (Arrow zero-copy). DuckDB 가 자동 disk-spill 로 OOC.
            - streaming 미지원 polars 연산 (asof/window 일부) 의 fallback.

        Guide:
            -

        When:
            호출 컨텍스트.

        How:
            구현.

        AIContext:
            폴라스 streaming 한계 만나면 본 엔진. caller 는 별도 SQL 작성 안 함 — 동일 인터페이스.

        Requires:
            - duckdb 패키지 (없으면 ImportError)

        SeeAlso:
            - :class:`PolarsCrossScan` — 기본 엔진
            - :func:`pickCrossScanEngine`
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

    Capabilities:
        - caller 우선 → 환경변수 ``DARTLAB_CROSS_SCAN_ENGINE`` 보조 → 기본 polars 의 3 단 우선
          순위 엔진 dispatcher.

    AIContext:
        cross-scan 엔진 선택을 caller 의 한 줄 호출로 해결. AI agent 가 메모리 압박 환경 (서버
        cron 등) 에 환경변수 "duckdb" 만 설정하면 본 함수가 자동 swap.

    Guide:
        - 명시 engine > env > 기본 polars 순. env 값은 case-insensitive.

    When:
        cross-company aggregation 호출 직전.

    How:
        engine 인자 또는 env var lookup → "duckdb" 이면 DuckDbCrossScan, 아니면 PolarsCrossScan.

    Requires:
        - polars (필수). duckdb 는 ``engine="duckdb"`` 선택 시 import 시점에 필요.

    SeeAlso:
        - :class:`PolarsCrossScan` · :class:`DuckDbCrossScan` — 두 구현
        - :class:`CrossScanEngine` — Protocol surface
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
