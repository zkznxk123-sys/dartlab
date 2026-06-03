"""EDGAR panel 통합 테스트 fixture — tmp dataDir 에 합성 원본 `.txt` + tickers.parquet 배치.

``data/original/edgar/docs/{cik}/{accession}.txt`` (합성 SEC submission) + ``data/edgar/tickers.parquet``
(ticker→cik) 을 tmp 에 깔고 ``config.dataDir`` monkeypatch + ``DARTLAB_NO_HF_DOWNLOAD`` 로 network 0.
builder/cellRead/panel round-trip 가 실제 build→read 경로를 그대로 탄다.
"""

from __future__ import annotations

import polars as pl
import pytest

import dartlab.config as _config

from .synthData import synthSubmissionTxt

_CIK = "0000012345"
_TICKER = "TEST"


@pytest.fixture
def builtTicker(tmp_path, monkeypatch):
    """tmp dataDir + 합성 원본/tickers 배치 → ticker 반환 (build 미실행 — 테스트가 직접 build)."""
    monkeypatch.setattr(_config, "dataDir", str(tmp_path))
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    edgarDir = tmp_path / "edgar"
    edgarDir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"cik": [_CIK], "ticker": [_TICKER], "title": ["TEST CORP"]}).write_parquet(
        str(edgarDir / "tickers.parquet")
    )
    docsDir = tmp_path / "original" / "edgar" / "docs" / _CIK
    docsDir.mkdir(parents=True, exist_ok=True)
    (docsDir / "0000012345-25-000001.txt").write_text(synthSubmissionTxt(), encoding="utf-8")
    return _TICKER
