"""SEC EDGAR listed universe cache helpers for ``core.dataLoader``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import polars as pl

LISTED_EXCHANGES = {"Nasdaq", "NYSE", "CBOE"}


def updateEdgarListedUniverse(
    *,
    force: bool,
    dataRoot: Path,
    ttlHours: int,
    listedUniverseUrl: str,
    fetchJson: Callable[[str], dict],
    isLocalCacheExpired: Callable[[Path, int], bool],
) -> Path:
    """SEC exchange ticker 원본으로 listed universe 캐시를 갱신한다."""
    path = dataRoot / "edgar" / "listedUniverse.parquet"
    if not force and path.exists() and not isLocalCacheExpired(path, ttlHours):
        return path

    from dartlab.core.messaging import emit

    emit("edgar:universe_update")
    data = fetchJson(listedUniverseUrl)

    records = []
    for row in data.get("data", []):
        if len(row) < 4:
            continue
        cik, name, ticker, exchange = row[:4]
        tickerStr = str(ticker or "").upper().strip()
        exchangeStr = str(exchange or "").strip()
        if not tickerStr:
            continue
        records.append(
            {
                "cik": str(cik).zfill(10),
                "ticker": tickerStr,
                "title": str(name or "").strip(),
                "exchange": exchangeStr,
                "is_exchange_listed": exchangeStr in LISTED_EXCHANGES,
                "is_otc": exchangeStr == "OTC",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(records).write_parquet(path)
    emit("edgar:universe_save", path=str(path))
    return path


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


__all__ = ["loadEdgarTargetUniverse", "loadSp500Tickers", "updateEdgarListedUniverse"]
