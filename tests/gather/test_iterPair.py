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


def test_iter_returns_generator(monkeypatch) -> None:
    """iter 메서드가 generator 객체 반환 (lazy) — fetch mock 으로 네트워크 회피."""
    from dartlab.gather.accessors import DefaultFinanceAccessor

    fa = DefaultFinanceAccessor()
    # fetch 가 빈 DataFrame 반환하도록 mock — generator 는 empty yield
    monkeypatch.setattr(fa, "fetchPriceSnapshot", lambda *a, **kw: pl.DataFrame({"x": list(range(25))}))
    gen = fa.iterPriceSnapshot("005930", batchSize=10)
    assert hasattr(gen, "__next__")
    batches = list(gen)
    assert len(batches) == 3  # 25 / 10 = 3 batches


def test_iterInsiderTrades_batches(monkeypatch) -> None:
    """iterInsiderTrades — fetchInsiderTrades 결과 mock 후 batch yield 검증."""
    from dartlab.gather.accessors import DefaultFinanceAccessor

    fa = DefaultFinanceAccessor()
    df = pl.DataFrame({"date": [f"2026-01-{i:02d}" for i in range(1, 16)], "amount": list(range(15))})
    monkeypatch.setattr(fa, "fetchInsiderTrades", lambda *a, **kw: df)

    batches = list(fa.iterInsiderTrades("005930", batchSize=7))
    assert len(batches) == 3
    assert batches[0].height == 7
    assert batches[1].height == 7
    assert batches[2].height == 1


def test_iterOwnership_batches(monkeypatch) -> None:
    """iterOwnership — fetchOwnership 결과 mock 후 batch yield."""
    from dartlab.gather.accessors import DefaultFinanceAccessor

    fa = DefaultFinanceAccessor()
    df = pl.DataFrame({"holder": [f"H{i}" for i in range(8)], "pct": [1.0] * 8})
    monkeypatch.setattr(fa, "fetchOwnership", lambda *a, **kw: df)

    batches = list(fa.iterOwnership("005930", batchSize=3))
    assert len(batches) == 3  # 8 / 3 = 3 batches (3, 3, 2)
    assert batches[-1].height == 2


def test_iterNews_batches(monkeypatch) -> None:
    """iterNews — fetchNews 결과 mock 후 batch yield."""
    from dartlab.gather.accessors import DefaultFinanceAccessor

    fa = DefaultFinanceAccessor()
    df = pl.DataFrame({"title": [f"news{i}" for i in range(12)], "url": ["x"] * 12})
    monkeypatch.setattr(fa, "fetchNews", lambda *a, **kw: df)

    batches = list(fa.iterNews("삼성전자", batchSize=5))
    assert len(batches) == 3  # 12 / 5 = 3 batches (5, 5, 2)
    assert batches[0].height == 5
    assert batches[-1].height == 2


def test_fetch_methods_return_none_when_empty(monkeypatch) -> None:
    """fetchInsiderTrades/fetchOwnership/fetchNews 가 빈 결과면 None 반환."""
    from dartlab.gather.accessors import DefaultFinanceAccessor
    from dartlab.gather.engine import Gather

    fa = DefaultFinanceAccessor()
    monkeypatch.setattr(Gather, "insiderTrading", lambda self, *a, **kw: [])
    monkeypatch.setattr(Gather, "ownership", lambda self, *a, **kw: [])
    monkeypatch.setattr(Gather, "news", lambda self, *a, **kw: pl.DataFrame())

    assert fa.fetchInsiderTrades("005930") is None
    assert fa.fetchOwnership("005930") is None
    assert fa.fetchNews("nothing") is None
