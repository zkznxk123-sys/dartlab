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
    """Return the scan prebuild output directory.

    Capabilities:
        Resolves the active scan output directory from the configured DartLab data root.

    AIContext:
        Builder modules should call this helper instead of hard-coding ``data/dart/scan``.

    Guide:
        Use at call time so tests and runtime configuration can override the data root.

    When:
        Called by scan prebuild writers before creating or reading generated parquet files.

    How:
        Delegates to ``dartlab.core.dataLoader._dataDir("scan")`` and wraps the result as ``Path``.

    Args:
        None.

    Returns:
        ``Path`` pointing at the scan output directory.

    Requires:
        Configured DartLab data root resolvable by ``_dataDir``.

    Raises:
        Propagates data-root resolution errors from ``_dataDir``.

    Example:
        >>> scanDir().name
        'scan'

    SeeAlso:
        ``docsDir``, ``financeDir``, and ``reportDir``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("scan"))


def docsDir() -> Path:
    """Return the raw docs parquet directory.

    Capabilities:
        Resolves the active raw disclosure-docs parquet directory.

    AIContext:
        Docs prebuilds use this as the source root for changes and text index generation.

    Guide:
        Keep source path resolution centralized here to avoid drift between builders.

    When:
        Called by docs scan builders before scanning raw document parquet files.

    How:
        Delegates to ``dartlab.core.dataLoader._dataDir("docs")`` and wraps the result as ``Path``.

    Args:
        None.

    Returns:
        ``Path`` pointing at the raw docs directory.

    Requires:
        Configured DartLab data root resolvable by ``_dataDir``.

    Raises:
        Propagates data-root resolution errors from ``_dataDir``.

    Example:
        >>> docsDir().name
        'docs'

    SeeAlso:
        ``scanDir`` and ``dartlab.scan.builders.kr.docs``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("docs"))


def panelDir() -> Path:
    """Return the panel parquet directory (docs.parquet 은퇴 → panel SSOT source).

    Capabilities:
        Resolves the active panel parquet directory — scan docs prebuilds(changes·
        docsIndex)의 본문 source root (docs.parquet 대체).

    AIContext:
        docs 농장 은퇴 후 scan 변화/인덱스 prebuild 의 공시 본문 출처.

    Guide:
        Keep panel source path centralized here to avoid drift.

    When:
        Called by docs scan builders(changes·docsIndex) before scanning panel parquet.

    How:
        Delegates to ``dartlab.core.dataLoader._dataDir("panel")`` and wraps as ``Path``.

    Args:
        None.

    Returns:
        ``Path`` pointing at the panel directory.

    Raises:
        Propagates data-root resolution errors from ``_dataDir``.

    Example:
        >>> panelDir().name
        'panel'

    SeeAlso:
        ``docsDir`` and ``dartlab.providers.dart.sections``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("panel"))


def financeDir() -> Path:
    """Return the raw finance parquet directory.

    Capabilities:
        Resolves the active raw finance parquet directory.

    AIContext:
        Finance scan builders use this source root before calendarization and account normalization.

    Guide:
        Use this helper instead of duplicating data-root category strings across builders.

    When:
        Called by finance prebuild code before iterating per-company parquet files.

    How:
        Delegates to ``dartlab.core.dataLoader._dataDir("finance")`` and wraps the result as ``Path``.

    Args:
        None.

    Returns:
        ``Path`` pointing at the raw finance directory.

    Requires:
        Configured DartLab data root resolvable by ``_dataDir``.

    Raises:
        Propagates data-root resolution errors from ``_dataDir``.

    Example:
        >>> financeDir().name
        'finance'

    SeeAlso:
        ``scanDir`` and ``dartlab.scan.builders.kr.financeBuild``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("finance"))


def reportDir() -> Path:
    """Return the raw report parquet directory.

    Capabilities:
        Resolves the active raw report parquet directory.

    AIContext:
        Report scan builders use this source root before API-type splitting.

    Guide:
        Keep report source path resolution centralized to preserve provider/runtime symmetry.

    When:
        Called by report prebuild code before iterating per-company report parquet files.

    How:
        Delegates to ``dartlab.core.dataLoader._dataDir("report")`` and wraps the result as ``Path``.

    Args:
        None.

    Returns:
        ``Path`` pointing at the raw report directory.

    Requires:
        Configured DartLab data root resolvable by ``_dataDir``.

    Raises:
        Propagates data-root resolution errors from ``_dataDir``.

    Example:
        >>> reportDir().name
        'report'

    SeeAlso:
        ``scanDir`` and ``dartlab.scan.builders.kr.report.build``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("report"))


def say(msg: str) -> None:
    """Emit a builder progress message.

    Capabilities:
        Writes scan builder progress through the package logger.

    AIContext:
        Keeps prebuild progress observable without mixing print calls into library code.

    Guide:
        Use for human-readable build progress only; structured metrics belong in callers.

    When:
        Called by long-running scan builders at stage boundaries and batch checkpoints.

    How:
        Forwards ``msg`` to ``logger.info`` for this module.

    Args:
        msg: Message to emit.

    Returns:
        ``None``.

    Requires:
        Module logger initialized by ``getLogger``.

    Raises:
        Logger backend errors, if the configured logger raises.

    Example:
        >>> say("scan build started")

    SeeAlso:
        ``dartlab.core.logger.getLogger``.
    """
    _log.info(msg)


def mergeBatchFiles(batchDir: Path, outputPath: Path, *, how: str = "vertical") -> int:
    """Merge ``batch_*.parquet`` files into ``outputPath`` and return row count.

    Capabilities:
        Combines batch parquet chunks into one compressed parquet file using Polars lazy concat.

    AIContext:
        Scan builders use this helper to avoid holding all company data in memory at once.

    Guide:
        Choose ``how="diagonal_relaxed"`` when source schemas differ by file or API type.

    When:
        Called at the end of a chunked prebuild stage after batch files have been flushed.

    How:
        Scans sorted ``batch_*.parquet`` files lazily, concatenates them, writes zstd parquet,
        then re-scans the output to return the materialized row count.

    Args:
        batchDir: Directory containing ``batch_*.parquet`` files.
        outputPath: Destination parquet path.
        how: Polars concat mode. Defaults to ``"vertical"``.

    Returns:
        Number of rows written to ``outputPath``. Returns ``0`` when no batch files exist.

    Requires:
        Readable parquet batch files and write permission for ``outputPath``.

    Raises:
        ``polars.PolarsError`` or ``OSError`` when scanning or writing parquet fails.

    Example:
        >>> rows = mergeBatchFiles(tmp_dir, tmp_dir / "merged.parquet")
        >>> rows >= 0
        True

    SeeAlso:
        ``financeBuild.buildFinance`` and ``report.build.buildReport``.
    """
    batchFiles = sorted(batchDir.glob("batch_*.parquet"))
    if not batchFiles:
        return 0

    lazyParts = [pl.scan_parquet(str(f)) for f in batchFiles]
    merged = pl.concat(lazyParts, how=how)
    merged.sink_parquet(str(outputPath), compression="zstd")
    return pl.scan_parquet(str(outputPath)).select(pl.len()).collect().item()
