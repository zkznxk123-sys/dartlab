"""EDGAR panel 통합 테스트 fixture — tmp dataDir 에 tickers.parquet 배치.

``data/edgar/tickers.parquet`` (ticker→cik) 을 tmp 에 깔고 ``config.dataDir`` monkeypatch +
``DARTLAB_NO_HF_DOWNLOAD`` 로 network 0. builder 는 합성 full-submission text 를 메모리로 받아 panel
단일 artifact 를 쓴다.
"""

from __future__ import annotations

import polars as pl
import pytest

import dartlab.config as _config

_CIK = "0000012345"
_TICKER = "TEST"


@pytest.fixture
def builtTicker(tmp_path, monkeypatch):
    """tmp dataDir + tickers 배치 → ticker 반환 (build 미실행 — 테스트가 직접 build)."""
    monkeypatch.setattr(_config, "dataDir", str(tmp_path))
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    edgarDir = tmp_path / "edgar"
    edgarDir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"cik": [_CIK], "ticker": [_TICKER], "title": ["TEST CORP"]}).write_parquet(
        str(edgarDir / "tickers.parquet")
    )
    return _TICKER
