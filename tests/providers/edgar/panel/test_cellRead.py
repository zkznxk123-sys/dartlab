"""EDGAR panel cellRead — native 셀 → 계정×기간 wide, DART readStatement 공개 계약 동형 (data 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_read_native_statement_contract(builtTicker) -> None:
    """readNative 출력 = DART 계약 [account, label, *period] (period 최신 좌측)."""
    from dartlab.providers.edgar.panel import cellRead
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    buildEdgarPanel(builtTicker)
    for st in ("is", "bs"):
        w = cellRead.readNative(builtTicker, statement=st, freq="year")
        assert w is not None, f"{st} None"
        assert w.columns[:2] == ["account", "label"], "DART 계약 [account, label, ...] 위반"
        assert "2024" in w.columns  # period 컬럼
        assert w.height > 0


def test_read_native_bs_populates(builtTicker) -> None:
    """BS(instant) 가 freq=year 에서 값을 채운다 (instant mode Y/A freq mask 정합)."""
    from dartlab.providers.edgar.panel import cellRead
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    buildEdgarPanel(builtTicker)
    bs = cellRead.readNative(builtTicker, statement="bs", freq="year")
    assert bs is not None and "2024" in bs.columns
    vals = bs["2024"].to_list()
    assert any(v is not None for v in vals), "BS 값 전부 null (instant mode 미정합)"


def test_read_native_absent_none(builtTicker, tmp_path, monkeypatch) -> None:
    """셀 artifact 부재 → None (예외 0)."""
    from dartlab.providers.edgar.panel import cellRead

    assert cellRead.readNative("ZZZZ", statement="is", freq="year") is None
