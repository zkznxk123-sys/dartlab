"""M6: CrossScanEngine Protocol + Polars/DuckDB 양 구현 동치 검증.

dartlab.scan.docsSections() 의 cross-company aggregation 엔진 dispatcher.
PolarsCrossScan (기본, streaming engine) 와 DuckDbCrossScan (OOC SQL 위임)
이 동일 LazyFrame 입력에 대해 동일 결과를 반환해야 한다.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.scan.io.cross import (
    CrossScanEngine,
    DuckDbCrossScan,
    PolarsCrossScan,
    pickCrossScanEngine,
)

pytestmark = pytest.mark.unit


def _fixtureLf() -> pl.LazyFrame:
    """3 회사 × 3 row LazyFrame — 단순 fixture."""
    return pl.LazyFrame(
        {
            "stockCode": ["005930", "005930", "000660", "000660", "035420"],
            "year": [2023, 2024, 2023, 2024, 2024],
            "sectionTitle": ["BS", "IS", "BS", "IS", "BS"],
            "contentLength": [1000, 2000, 1500, 2500, 3000],
        }
    )


class TestProtocolImplements:
    """PolarsCrossScan / DuckDbCrossScan 가 CrossScanEngine Protocol 만족."""

    def test_polars_implements_protocol(self):
        assert isinstance(PolarsCrossScan(), CrossScanEngine)

    def test_duckdb_implements_protocol(self):
        assert isinstance(DuckDbCrossScan(), CrossScanEngine)


class TestEquivalence:
    """양 엔진 동일 결과 — Protocol contract."""

    def test_no_filter_same_result(self):
        """필터 없음 — 전체 5 row 동일."""
        lf = _fixtureLf()
        pdf = PolarsCrossScan().aggregate(lf)
        ddf = DuckDbCrossScan().aggregate(lf)
        # 같은 행 수, 같은 컬럼 set
        assert pdf.height == ddf.height == 5
        assert set(pdf.columns) == set(ddf.columns)

    def test_filter_year_2024(self):
        """year=2024 필터 — 3 row 동일."""
        lf = _fixtureLf().filter(pl.col("year") == 2024)
        pdf = PolarsCrossScan().aggregate(lf)
        ddf = DuckDbCrossScan().aggregate(lf)
        assert pdf.height == ddf.height == 3

    def test_limit_applied(self):
        """limit=2 동일 적용."""
        lf = _fixtureLf()
        pdf = PolarsCrossScan().aggregate(lf, limit=2)
        ddf = DuckDbCrossScan().aggregate(lf, limit=2)
        assert pdf.height == ddf.height == 2


class TestDispatcher:
    """pickCrossScanEngine 토글."""

    def test_default_is_polars(self, monkeypatch):
        """env 미설정 시 기본 PolarsCrossScan."""
        monkeypatch.delenv("DARTLAB_CROSS_SCAN_ENGINE", raising=False)
        engine = pickCrossScanEngine()
        assert isinstance(engine, PolarsCrossScan)

    def test_env_duckdb(self, monkeypatch):
        """``DARTLAB_CROSS_SCAN_ENGINE=duckdb`` 환경변수 시 DuckDbCrossScan."""
        monkeypatch.setenv("DARTLAB_CROSS_SCAN_ENGINE", "duckdb")
        engine = pickCrossScanEngine()
        assert isinstance(engine, DuckDbCrossScan)

    def test_explicit_duckdb_overrides_env(self, monkeypatch):
        """``engine="duckdb"`` 명시 시 env 와 무관 DuckDbCrossScan."""
        monkeypatch.setenv("DARTLAB_CROSS_SCAN_ENGINE", "polars")
        engine = pickCrossScanEngine(engine="duckdb")
        assert isinstance(engine, DuckDbCrossScan)

    def test_explicit_polars_overrides_env(self, monkeypatch):
        """``engine="polars"`` 명시 시 env 와 무관 PolarsCrossScan."""
        monkeypatch.setenv("DARTLAB_CROSS_SCAN_ENGINE", "duckdb")
        engine = pickCrossScanEngine(engine="polars")
        assert isinstance(engine, PolarsCrossScan)
