"""iter pair pattern 검증 — accessors 5 iter generator + 헬퍼 (G+ P-Q6).

providers 룰 10 (iter pair) 정신 차용. fetch* 의 single-shot DataFrame 결과
+ iter* 의 batch streaming 동행. 메모리 효율 + 사용자 선택권.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_iterDataFrameBatches_helper() -> None:
    """공통 헬퍼 — 25 행 DataFrame 을 batchSize=10 으로 → 3 batch."""
    from dartlab.gather.accessors import _iterDataFrameBatches

    df = pl.DataFrame({"x": list(range(25))})
    batches = list(_iterDataFrameBatches(df, 10))
    assert len(batches) == 3
    assert batches[0].height == 10
    assert batches[1].height == 10
    assert batches[2].height == 5


def test_iterDataFrameBatches_none() -> None:
    """None 입력 시 빈 generator (yield 없음)."""
    from dartlab.gather.accessors import _iterDataFrameBatches

    batches = list(_iterDataFrameBatches(None, 10))
    assert batches == []


def test_iterDataFrameBatches_empty() -> None:
    """height=0 DataFrame 도 yield 없음."""
    from dartlab.gather.accessors import _iterDataFrameBatches

    df = pl.DataFrame(schema={"x": pl.Int64})
    batches = list(_iterDataFrameBatches(df, 10))
    assert batches == []


def test_iter_methods_exist() -> None:
    """5 iter 메서드 모두 존재 + callable."""
    from dartlab.gather.accessors import (
        DefaultFinanceAccessor,
        DefaultIndustryAccessor,
        DefaultQuantAccessor,
    )

    fa = DefaultFinanceAccessor()
    qa = DefaultQuantAccessor()
    ia = DefaultIndustryAccessor()
    assert callable(fa.iterPriceSnapshot)
    assert callable(fa.iterMacroSeries)
    assert callable(qa.iterUniverseBulk)
    assert callable(ia.iterListing)
    assert callable(ia.iterScanFinanceParquet)


def test_iter_returns_generator() -> None:
    """iter 메서드가 generator 객체 반환 (lazy)."""
    from dartlab.gather.accessors import DefaultFinanceAccessor

    fa = DefaultFinanceAccessor()
    gen = fa.iterPriceSnapshot("__INVALID__", batchSize=10)
    # fetch 가 실패해도 generator 자체는 정상 반환
    assert hasattr(gen, "__next__")
    # consume (None 이면 yield 안 함 → 0 batches)
    batches = list(gen)
    assert isinstance(batches, list)  # 빈 리스트 또는 batches
