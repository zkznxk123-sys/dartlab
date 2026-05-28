"""handlePrice 의 ISIN/FIGI 자동 감지 — Sprint 3 PR3.

symbology live 호출은 monkeypatch — _maybeResolveAssetId 분기만 검증.
"""

from __future__ import annotations

import pytest

from dartlab.gather.entry import handlers
from dartlab.gather.entry.handlers import _maybeResolveAssetId

pytestmark = pytest.mark.unit


def test_ticker_no_resolution_noop() -> None:
    """일반 ticker (ISIN/FIGI 형식 아님) → 원본 그대로."""
    target, market = _maybeResolveAssetId("AAPL", "US", False)
    assert target == "AAPL"
    assert market == "US"


def test_none_target_noop() -> None:
    """None target → 그대로."""
    target, market = _maybeResolveAssetId(None, "KR", False)
    assert target is None
    assert market == "KR"


def test_korean_stock_code_noop() -> None:
    """한국 종목 코드 6자리 — ISIN 형식 매치 안 됨."""
    target, market = _maybeResolveAssetId("005930", "KR", False)
    assert target == "005930"
    assert market == "KR"


def test_isin_resolved_to_ticker(monkeypatch) -> None:
    """ISIN 12자 → symbology.isinToTicker 호출 → ticker 반환."""
    monkeypatch.setattr(
        handlers,
        "isinToTicker",
        lambda *args, **kwargs: None,
        raising=False,
    )
    # symbology import 가 _maybeResolveAssetId 내부에서 일어남 — direct monkeypatch
    from dartlab.gather.mapping import symbology

    monkeypatch.setattr(symbology, "isinToTicker", lambda x, **kwargs: ("AAPL", "US"))
    target, market = _maybeResolveAssetId("US0378331005", "KR", False)
    assert target == "AAPL"
    assert market == "US"  # OpenFIGI exch=US → marketConfig US


def test_isin_resolution_fail_returns_original(monkeypatch) -> None:
    """isinToTicker None → 원본 ISIN + market 유지."""
    from dartlab.gather.mapping import symbology

    monkeypatch.setattr(symbology, "isinToTicker", lambda x, **kwargs: None)
    target, market = _maybeResolveAssetId("XX0000000000", "KR", False)
    assert target == "XX0000000000"
    assert market == "KR"


def test_isin_marketExplicit_preserves_market(monkeypatch) -> None:
    """marketExplicit=True → 사용자 명시 market 유지 (OpenFIGI exch 무시)."""
    from dartlab.gather.mapping import symbology

    monkeypatch.setattr(symbology, "isinToTicker", lambda x, **kwargs: ("AAPL", "US"))
    target, market = _maybeResolveAssetId("US0378331005", "JP", True)
    assert target == "AAPL"
    assert market == "JP"  # 명시 → 변경 안 됨


def test_figi_resolved_to_ticker(monkeypatch) -> None:
    """FIGI 12자 BBG prefix → figiToTicker 호출."""
    from dartlab.gather.mapping import symbology

    monkeypatch.setattr(symbology, "figiToTicker", lambda x, **kwargs: ("MSFT", "US"))
    target, market = _maybeResolveAssetId("BBG000BPH459", "KR", False)
    assert target == "MSFT"
    assert market == "US"


def test_symbology_exception_silent(monkeypatch) -> None:
    """symbology 가 raise 해도 handler 흐름 차단 안 됨 — 원본 반환."""
    from dartlab.gather.mapping import symbology

    def _boom(*args, **kwargs):
        raise RuntimeError("OpenFIGI down")

    monkeypatch.setattr(symbology, "isinToTicker", _boom)
    target, market = _maybeResolveAssetId("US0378331005", "KR", False)
    assert target == "US0378331005"
    assert market == "KR"


def test_invalid_isin_format_noop() -> None:
    """11자 (체크섬 누락) → ISIN 매치 안 됨 → symbology 호출 안 됨."""
    target, market = _maybeResolveAssetId("US037833100", "KR", False)
    assert target == "US037833100"
    assert market == "KR"
