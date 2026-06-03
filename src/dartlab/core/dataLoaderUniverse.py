"""SEC EDGAR listed universe read/filter helpers for ``core.dataLoader``.

NOTE: universe 갱신(SEC ``company_tickers_exchange.json`` fetch+build)은
gather/edgar/universe 로 이관(수집 일원화). 본 모듈은 캐시 parquet 의 tier 필터·
정적 S&P500 교차(network 0)만 담당.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl


def loadEdgarTargetUniverse(universe: pl.DataFrame, tier: str, sp500Tickers: list[str] | None) -> pl.DataFrame:
    """tier별 EDGAR 상장사 목록을 필터링한다."""
    listed = universe.filter(pl.col("is_exchange_listed"))

    if tier == "all":
        return listed
    if tier == "nasdaq":
        return listed.filter(pl.col("exchange") == "Nasdaq")
    if tier == "nyse":
        return listed.filter(pl.col("exchange") == "NYSE")
    if tier == "sp500":
        if sp500Tickers is not None:
            return listed.filter(pl.col("ticker").is_in(sp500Tickers))
        return listed
    return listed


def loadSp500Tickers(repoRoot: Path) -> list[str] | None:
    """정적 S&P 500 ticker 목록 로드 (`.github/data/edgarTickers.json` fallback)."""
    candidates = [
        repoRoot / ".github" / "data" / "edgarTickers.json",
    ]
    for fp in candidates:
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            tickers = data.get("sp500", [])
            return tickers if tickers else None
    return None


__all__ = ["loadEdgarTargetUniverse", "loadSp500Tickers"]
