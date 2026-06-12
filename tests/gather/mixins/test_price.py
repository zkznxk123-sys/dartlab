"""dartlab.gather.mixins.price mirror 슬롯 — smoke import (P-G7.2).

룰 7 (src↔tests 1:1 mirror) 만족용 placeholder. 본격 단위 테스트는 후속.
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.mixins.price`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.mixins.price")


def test_price_auto_detects_us_ticker() -> None:
    """Gather.price("AAPL") 는 market 인자 없이 US history 로 라우팅한다."""
    from dartlab.gather.mixins.price import _GatherPriceMixin

    seen = {}

    class Dummy:
        def history(self, stockCode, *, start, end, market):
            seen.update({"stockCode": stockCode, "start": start, "end": end, "market": market})
            return pl.DataFrame({"date": [], "close": []})

    result = _GatherPriceMixin.price(Dummy(), "AAPL")

    assert isinstance(result, pl.DataFrame)
    assert seen["stockCode"] == "AAPL"
    assert seen["market"] == "US"
