"""providers/dart/docs/finance/shareCapital.py mirror smoke — P6."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.shareCapital  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_shares_outstanding_scan_callable() -> None:
    """buildSharesOutstandingScan() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import buildSharesOutstandingScan

    assert callable(buildSharesOutstandingScan)


def test_build_shares_outstanding_safe_accepts_snake_stock_code(monkeypatch) -> None:
    """wrapper 로깅이 canonical ``stock_code`` 산출물을 깨지 않는다."""
    import polars as pl

    from dartlab.scan.builders.kr import shares

    def fakeBuildSharesOutstandingScan() -> pl.DataFrame:
        return pl.DataFrame(
            [
                {"stock_code": "005930", "outstandingShares": 100},
                {"stock_code": "000660", "outstandingShares": 200},
            ]
        )

    monkeypatch.setattr(
        "dartlab.providers.dart.docs.finance.shareCapital.buildSharesOutstandingScan",
        fakeBuildSharesOutstandingScan,
    )
    monkeypatch.setattr(shares, "_scanDir", lambda: Path("."))
    messages: list[str] = []
    monkeypatch.setattr(shares, "_say", messages.append)

    assert shares.buildSharesOutstandingSafe(verbose=True) is not None
    assert any("stocks=2" in msg for msg in messages)


def test_parse_share_capital_table_callable() -> None:
    """parseShareCapitalTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import parseShareCapitalTable

    assert callable(parseShareCapitalTable)


def test_share_capital_callable() -> None:
    """shareCapital() callable smoke."""
    from dartlab.providers.dart.docs.finance.shareCapital import shareCapital

    assert callable(shareCapital)
