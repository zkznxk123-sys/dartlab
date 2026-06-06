"""scan 엔진 실제 데이터 스모크 — 전종목 횡단 프리빌드."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import polars as pl
import pytest


@lru_cache(maxsize=None)
def _scanUniqueStockCount(parquetName: str) -> int | None:
    from dartlab.scan.builders.kr.common import scanDir

    path = Path(scanDir()) / parquetName
    if not path.exists():
        return None
    try:
        lf = pl.scan_parquet(path)
        schema = lf.collect_schema()
        stock_col = (
            "stockCode" if "stockCode" in schema.names() else "stock_code" if "stock_code" in schema.names() else None
        )
        if stock_col is None:
            return None
        return int(lf.select(pl.col(stock_col).n_unique().alias("stocks")).collect().item(0, "stocks"))
    except (OSError, pl.exceptions.PolarsError):
        return None


def _coverageMinHeight(default: int, *, parquetName: str = "finance.parquet") -> int:
    unique_stocks = _scanUniqueStockCount(parquetName)
    if unique_stocks is None or unique_stocks >= default:
        return default
    return max(1, int(unique_stocks * 0.8))


def _assertFrame(result, name: str, *, minHeight: int = 1):
    """scan 결과가 실제 DataFrame 이고 비어 있지 않은지 확인."""
    assert result is not None, f"{name} 결과가 None"
    assert isinstance(result, pl.DataFrame), f"{name} 결과 타입이 DataFrame 아님: {type(result).__name__}"
    assert result.height >= minHeight, f"{name} 결과가 너무 작음: {result.height} < {minHeight}"
    return result


@pytest.mark.realData
@pytest.mark.integration
class TestScanEngine:
    """dartlab.scan(axis=...) 가 프리빌드 parquet 에서 즉시 로드 가능."""

    def test_axes_listed(self):
        """scan 이 노출하는 축 목록."""
        import dartlab

        axes = dartlab.scan.availableScans()
        assert axes
        assert isinstance(axes, list)

    def test_scanCallable_runsOnSampleAxis(self):
        """첫 번째 축을 실제로 호출해 None/빈 결과가 아님을 검증."""
        import dartlab

        axes = dartlab.scan.availableScans()
        if not axes:
            pytest.skip("scan axis 목록이 비어있음")
        sampleAxis = axes[0]
        result = dartlab.scan(axis=sampleAxis)
        # scan 은 DataFrame 또는 dict 반환 가능
        assert result is not None
        if hasattr(result, "height"):
            assert result.height > 0
        else:
            assert result, f"{sampleAxis} 축이 빈 결과"

    def test_scanAccountSales_explicit(self):
        """사용자 대표 호출: dartlab.scan("account", "매출액")."""
        import dartlab
        from dartlab.core.memory import MemoryBudgetExceeded

        try:
            result = dartlab.scan("account", "매출액")
        except MemoryBudgetExceeded as e:
            pytest.fail(f"scan('account', '매출액') 메모리 예산 회귀: {e}")
        df = _assertFrame(result, "scan.account.sales", minHeight=_coverageMinHeight(1000))
        periodCols = [col for col in df.columns if str(col)[:4].isdigit()]
        assert periodCols, "scan.account.sales 기간 컬럼 없음"

    def test_scanRatioRoe_explicit(self):
        """사용자 대표 호출: dartlab.scan("ratio", "roe")."""
        import dartlab
        from dartlab.core.memory import MemoryBudgetExceeded

        try:
            result = dartlab.scan("ratio", "roe")
        except MemoryBudgetExceeded as e:
            pytest.fail(f"scan('ratio', 'roe') 메모리 예산 회귀: {e}")
        df = _assertFrame(result, "scan.ratio.roe", minHeight=_coverageMinHeight(1000))
        periodCols = [col for col in df.columns if str(col)[:4].isdigit()]
        assert periodCols, "scan.ratio.roe 기간 컬럼 없음"

    def test_scanValuation_explicit(self):
        """사용자 대표 호출: dartlab.scan("valuation")."""
        import dartlab

        result = dartlab.scan("valuation")
        _assertFrame(result, "scan.valuation", minHeight=100)
