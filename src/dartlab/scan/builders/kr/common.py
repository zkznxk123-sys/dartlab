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

import ctypes
import gc
import json
import os
from pathlib import Path

import polars as pl

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


def configuredBatchSize(default: int = 200) -> int:
    """Return scan-builder batch size, optionally capped by env for constrained runners."""
    raw = os.environ.get("DARTLAB_SCAN_BATCH_SIZE", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


BATCH_SIZE = configuredBatchSize()


def releaseNativeMemory() -> None:
    """Ask Python and the libc allocator to return freed Polars/native memory."""
    gc.collect()
    if os.name != "posix":
        return
    try:
        trim = getattr(ctypes.CDLL("libc.so.6"), "malloc_trim", None)
    except OSError:
        return
    if trim is not None:
        trim(0)


# 증분 prebuild 변경 감지 ledger 파일명 (scanDir 아래). panel HF listing 의
# {filename: size} 스냅샷을 직전 빌드가 남기고, 다음 사이클이 size 차이로 변경 종목을 가린다.
SCAN_BUILD_STATE_FILE = "_scanBuildState.json"


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
        ``panelDir``, ``financeDir``, and ``reportDir``.
    """
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("scan"))


def panelDir() -> Path:
    """Return the panel parquet directory.

    Capabilities:
        Resolves the active panel parquet directory — scan docs prebuilds(changes·
        docsIndex)의 본문 source root.

    AIContext:
        scan 변화/인덱스 prebuild 의 공시 본문 출처.

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
        ``docsDir`` and ``dartlab.providers.dart.panel.text``.
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


def loadScanBuildState() -> dict[str, int]:
    """직전 prebuild 가 남긴 panel 변경 감지 ledger 를 읽는다.

    Args:
        없음.

    Returns:
        ``{panelFilename: sizeBytes}`` dict. ledger 부재/파손 시 빈 dict.

    Raises:
        없음 — 파일 부재·JSON 파손은 빈 dict 로 흡수(증분 대신 full 로 안전 폴백).

    Example:
        >>> isinstance(loadScanBuildState(), dict)
        True
    """
    statePath = scanDir() / SCAN_BUILD_STATE_FILE
    if not statePath.exists():
        return {}
    try:
        raw = json.loads(statePath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): int(v) for k, v in raw.items() if isinstance(v, (int, float))}


def saveScanBuildState(state: dict[str, int]) -> Path:
    """panel 변경 감지 ledger 를 scanDir 에 기록한다 (다음 사이클 변경 가림용).

    Args:
        state: ``{panelFilename: sizeBytes}`` — 보통 ``hfGateway.hfList("panel")`` 결과.

    Returns:
        기록된 ledger 경로.

    Raises:
        OSError: 쓰기 실패 시.

    Example:
        >>> p = saveScanBuildState({"005930.parquet": 1234})  # doctest: +SKIP
    """
    out = scanDir()
    out.mkdir(parents=True, exist_ok=True)
    statePath = out / SCAN_BUILD_STATE_FILE
    statePath.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return statePath


def mergeIncremental(existingPath: Path, rebuilt: pl.DataFrame, *, key: str = "stockCode") -> int:
    """재계산 행(rebuilt)을 기존 scan parquet 에 종목 단위로 갈아끼운다.

    기존 parquet 에서 ``rebuilt[key]`` 에 속한 종목 행을 드롭하고 rebuilt 를 append 한 뒤
    ``existingPath`` 에 zstd 로 다시 쓴다. 증분 빌더가 변경 종목만 재계산했을 때, 전 종목
    parquet 을 재생성하지 않고 해당 종목 슬라이스만 교체하는 단일 진입점이다.

    Args:
        existingPath: 직전 사이클 산출 parquet (HF 에서 seed 된 것). 없으면 rebuilt 그대로 기록.
        rebuilt: 변경 종목만 재계산한 DataFrame. 빈 DataFrame 이면 기존 보존(no-op write).
        key: 종목 식별 컬럼 (changes/docsIndex=``stockCode``, shares=``stock_code``).

    Returns:
        병합 후 최종 행 수.

    Raises:
        polars.PolarsError: parquet read/write 실패 시.

    Example:
        >>> import polars as pl
        >>> n = mergeIncremental(Path("/tmp/x.parquet"), pl.DataFrame({"stockCode": ["1"]}))  # doctest: +SKIP
    """
    existingPath = Path(existingPath)
    if rebuilt.is_empty() and existingPath.exists():
        return pl.scan_parquet(str(existingPath)).select(pl.len()).collect().item()

    if existingPath.exists():
        changedKeys = rebuilt.get_column(key).unique().to_list()
        prior = pl.read_parquet(str(existingPath)).filter(~pl.col(key).is_in(changedKeys))
        # 서로 다른 parquet 소스의 Categorical 은 string-cache 가 달라 concat 시 충돌 →
        # 방어적으로 Utf8 로 풀어 합친다(Categorical 은 저장 size 최적화일 뿐, 의미 동일).
        combined = pl.concat([_decategorize(prior), _decategorize(rebuilt)], how="diagonal_relaxed")
    else:
        combined = _decategorize(rebuilt)

    existingPath.parent.mkdir(parents=True, exist_ok=True)
    combined.write_parquet(str(existingPath), compression="zstd")
    return combined.height


def _decategorize(df: pl.DataFrame) -> pl.DataFrame:
    """Categorical 컬럼을 Utf8 로 캐스팅 (cross-source concat string-cache 충돌 회피)."""
    catCols = [c for c, dt in zip(df.columns, df.dtypes, strict=False) if dt == pl.Categorical]
    return df.with_columns([pl.col(c).cast(pl.Utf8) for c in catCols]) if catCols else df


def pruneScanCodes(existingPath: Path, removedCodes: list[str], *, key: str = "stockCode") -> int:
    """상장폐지 등으로 사라진 종목 행을 기존 scan parquet 에서 제거한다(다운로드 불요).

    panel HF listing 에서 빠진 종목은 panel 파일을 받지 않고도 ledger diff 로 식별 가능하다.
    증분 사이클이 add/change(다운로드 후 :func:`mergeIncremental`) 와 delete(본 함수) 를 모두
    덮어 daily 경로만으로 데이터 drift 가 누적되지 않게 한다.

    Args:
        existingPath: 정리 대상 parquet. 없으면 0 반환(no-op).
        removedCodes: 제거할 종목코드 목록(파일 stem). 빈 목록이면 no-op.
        key: 종목 식별 컬럼.

    Returns:
        제거된 행 수.

    Raises:
        polars.PolarsError: parquet read/write 실패 시.

    Example:
        >>> pruneScanCodes(Path("/tmp/none.parquet"), ["009999"])
        0
    """
    existingPath = Path(existingPath)
    if not removedCodes or not existingPath.exists():
        return 0
    df = pl.read_parquet(str(existingPath))
    before = df.height
    df = df.filter(~pl.col(key).is_in(removedCodes))
    removed = before - df.height
    if removed:
        df.write_parquet(str(existingPath), compression="zstd")
    return removed
