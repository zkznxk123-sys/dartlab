"""dartlab.gather.sources.news real unit test (A 트랙 I2 + T2).

iterFetchNews generator + fetchNews 본문 검증.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.sources.news`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.sources.news")


def test_iterFetchNews_yields(monkeypatch: pytest.MonkeyPatch) -> None:
    """iterFetchNews — fetchNews 결과 mock 후 batch yield (A 트랙 I2)."""
    from dartlab.gather.sources import news as newsMod

    df = pl.DataFrame({"title": [f"t{i}" for i in range(12)], "url": ["x"] * 12})
    monkeypatch.setattr(newsMod, "fetchNews", lambda *a, **kw: df)

    batches = list(newsMod.iterFetchNews("test", batchSize=5))
    assert len(batches) == 3
    assert batches[0].height == 5
    assert batches[-1].height == 2


def test_iterFetchNews_empty_df(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetchNews 가 빈 DataFrame 이면 iter generator 도 빈 yield."""
    from dartlab.gather.sources import news as newsMod

    monkeypatch.setattr(newsMod, "fetchNews", lambda *a, **kw: pl.DataFrame())
    batches = list(newsMod.iterFetchNews("nothing"))
    assert batches == []
