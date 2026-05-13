"""Shared utilities for KR scan builders.

Capabilities:
    - Provides shared builder path, logging, batch size, and parquet merge helpers.

Args:
    Path helpers take no arguments. ``mergeBatchFiles`` accepts batch/output paths.

Returns:
    ``Path`` helpers return directories; ``mergeBatchFiles`` returns merged row count.

Example:
    >>> scanDir().name
    'scan'

Guide:
    Keep this module narrow. Only helpers used by multiple builders belong here.

SeeAlso:
    ``core``, ``docs.changes``, and ``financeLite``.

Requires:
    ``dartlab.core.dataLoader`` for active data-root resolution.

AIContext:
    Avoids repeated path/batch helpers without creating tiny over-split utility folders.

LLM Specifications:
    AntiPatterns: Do not add finance/report/docs domain transforms here.
    OutputSchema: Path helpers return ``Path``; merge helper returns ``int``.
    Prerequisites: Caller is a scan prebuild module.
    Freshness: No data freshness policy; paths are resolved at call time.
    Dataflow: builder -> common helper -> path/log/merged parquet result.
    TargetMarkets: KR scan prebuild internals.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)

BATCH_SIZE = 200


def scanDir() -> Path:
    """Return the scan prebuild output directory."""
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("scan"))


def docsDir() -> Path:
    """Return the raw docs parquet directory."""
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("docs"))


def financeDir() -> Path:
    """Return the raw finance parquet directory."""
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("finance"))


def reportDir() -> Path:
    """Return the raw report parquet directory."""
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("report"))


def say(msg: str) -> None:
    """Emit a builder progress message."""
    _log.info(msg)


def mergeBatchFiles(batchDir: Path, outputPath: Path, *, how: str = "vertical") -> int:
    """Merge ``batch_*.parquet`` files into ``outputPath`` and return row count."""
    batchFiles = sorted(batchDir.glob("batch_*.parquet"))
    if not batchFiles:
        return 0

    lazyParts = [pl.scan_parquet(str(f)) for f in batchFiles]
    merged = pl.concat(lazyParts, how=how)
    merged.sink_parquet(str(outputPath), compression="zstd")
    return pl.scan_parquet(str(outputPath)).select(pl.len()).collect().item()
