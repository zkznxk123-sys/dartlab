"""panel 전종목 batch 빌드 (L1 build, multiprocessing) — builder 단일 빌드의 fan-out.

``builder.buildPanel`` 을 종목별 worker 로 병렬 실행 (strict per-corp, memory 무관). ref table 은
``_initWorker`` 가 worker 당 1회 load + token pre-compute → 매 row matchToRef 의 row iter 회피.
단일 빌드(buildPanel/buildPanelBaseline)는 ``builder`` 에, 본 모듈은 병렬 fan-out + CLI entry 만.

LLM Specifications:
    AntiPatterns:
        - Pool.map 금지 — large input memory 폭발. imap_unordered chunk.
        - worker 간 ref 재로드 금지 — _initWorker 1회 load.
        - 단일 빌드 로직 중복 금지 — builder.buildPanel 위임.
    OutputSchema:
        - ``buildPanelAll(*, refPath, outBaseDir, codes, numWorkers) -> dict[code, (periodCount, totalRow)]``.
    Prerequisites:
        - 전종목 zip + ref parquet. multiprocessing.
    Freshness:
        - 분기 incremental — changed code 만.
    Dataflow:
        - codes → Pool(_initWorker) → _buildOne(builder.buildPanel) → 집계.
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

from .builder import buildPanel, buildPanelBaseline, panelXbrlRefPath

_log = logging.getLogger(__name__)

_GLOBAL_REF: pl.DataFrame | None = None


def _initWorker(refPath: str) -> None:
    """multiprocessing worker init — ref table load + token pre-compute.

    refMatcher token set 을 worker 시작 시 한 번 계산 → 매 row matchToRef 의 row iter 회피.

    Args:
        refPath: ref parquet 경로.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> _initWorker("data/dart/panelXbrlRef.parquet")  # doctest: +SKIP
    """
    global _GLOBAL_REF
    _GLOBAL_REF = pl.read_parquet(refPath)
    from .refScan.refMatcher import precomputeRefTokens, setGlobalRefTokens

    setGlobalRefTokens(precomputeRefTokens(_GLOBAL_REF))


def _buildOne(args: tuple[str, str, str]) -> tuple[str, int, int, float]:
    """worker entry — (code, refPath, outBaseDir) → (code, periodCount, totalRow, elapsed).

    Args:
        args: ``(code, refPath, outBaseDir)`` 튜플. pickleable.

    Returns:
        ``(code, periodCount, totalRow, elapsed)``. 실패 시 (code, 0, 0, elapsed).

    Raises:
        없음 — 빌드 실패 흡수.

    Example:
        >>> _buildOne(("005930", "ref.parquet", "data/dart/panel"))  # doctest: +SKIP
    """
    code, refPath, outBaseDir = args
    global _GLOBAL_REF
    t0 = time.perf_counter()
    try:
        ref = _GLOBAL_REF
        if ref is None:
            ref = pl.read_parquet(refPath)
        result = buildPanel(code, refDf=ref, outBaseDir=Path(outBaseDir), overwrite=True, verbose=False)
        return (code, len(result), sum(result.values()), time.perf_counter() - t0)
    except (OSError, ValueError, RuntimeError, MemoryError, pl.exceptions.PolarsError) as exc:
        # MemoryError 포함 — 거대 회사(금융지주 등 대용량 XML)가 worker 를 죽여 전체 Pool 을 깨지 않게 흡수.
        # 실패(failed) 로 기록 → resumable 재실행(skipExisting)이 메모리 여유 시 재시도. maxtasksperchild 가
        # 누적 힙을 주기 방출하므로 후속 종목은 정상 진행.
        _log.warning("buildPanel 실패 %s: %s", code, type(exc).__name__)
        return (code, 0, 0, time.perf_counter() - t0)


def buildPanelAll(
    *,
    refPath: str | Path | None = None,  # None = 패키지 동봉 panelXbrlRefPath() (data/ 아님)
    outBaseDir: str | Path = "data/dart/panel",
    codes: list[str] | None = None,
    numWorkers: int = 8,
    skipExisting: bool = True,  # resumable — 이미 빌드된 {code}.parquet 건너뜀 (크래시 후 재실행 이어감)
    progressEvery: int = 50,
    verbose: bool = True,
) -> dict[str, tuple[int, int]]:
    """전종목 panel 빌드 — multiprocessing.

    Args:
        refPath: panelXbrlRef ref parquet.
        outBaseDir: 출력 base dir.
        codes: 종목 list. None = ``data/original/dart/docs/`` 의 모든 종목.
        numWorkers: Pool workers (IO heavy, 기본 8).
        progressEvery: 진행 로그 빈도.
        verbose: 진행 로그.

    Returns:
        ``{code: (periodCount, totalRow)}`` dict.

    Raises:
        없음 — 종목별 실패 흡수.

    Example:
        >>> buildPanelAll(codes=["005930", "005380"])  # doctest: +SKIP

    SeeAlso:
        - ``builder.buildPanel`` — 단일 종목 빌드 (worker 가 위임).
        - ``builder.buildPanelBaseline`` — 5 baseline 검증.

    Requires:
        - data/original/dart/docs/{code}/*.zip 전종목. multiprocessing.

    Capabilities:
        - 전종목(~2,900) panel artifact 일괄 생산 (8코어 ~2.6h).

    Guide:
        - CI sync 잡 또는 운영자. memory 무관(strict per-corp worker).

    AIContext:
        - imap_unordered chunk=4 — IO/CPU 균형.

    When:
        - 전종목(또는 changed codes) 을 일괄 빌드할 때 (CI sync / 운영자).

    How:
        - Pool(_initWorker) 로 종목별 builder.buildPanel 병렬 실행 → 통계 집계.

    LLM Specifications:
        AntiPatterns:
            - Pool.map 금지 — large input memory 폭발. imap_unordered.
            - worker 간 ref 재로드 금지 — _initWorker 1회 load.
        OutputSchema:
            - ``dict[str, tuple[int, int]]``.
        Prerequisites:
            - 전종목 zip + ref parquet.
        Freshness:
            - 분기 incremental — changed code 만.
        Dataflow:
            - codes → Pool(_initWorker) → _buildOne → 집계.
        TargetMarkets:
            - KR (DART).
    """
    if codes is None:
        baseDir = Path(_cfg.dataDir) / "original" / "dart" / "docs"
        codes = sorted([d.name for d in baseDir.iterdir() if d.is_dir()])

    refPathStr = str(refPath if refPath is not None else panelXbrlRefPath())  # 패키지 동봉 ref (data/ 아님)
    outBaseStr = str(outBaseDir)
    Path(outBaseStr).mkdir(parents=True, exist_ok=True)

    if skipExisting:  # resumable — 이미 빌드 산출 있는 종목 제외 (크래시·중단 후 재실행이 이어감)
        total = len(codes)
        codes = [c for c in codes if not (Path(outBaseStr) / f"{c}.parquet").exists()]
        if verbose:
            _log.info("buildPanelAll: skipExisting — %d/%d 잔여 (%d 이미 빌드)", len(codes), total, total - len(codes))

    if verbose:
        _log.info("buildPanelAll: %d 종목, %d workers", len(codes), numWorkers)

    args = [(c, refPathStr, outBaseStr) for c in codes]
    result: dict[str, tuple[int, int]] = {}
    processed = 0
    failed = 0
    totalRows = 0
    t0 = time.perf_counter()
    # maxtasksperchild — worker 를 N 종목마다 재시작해 Polars Rust 힙 누적(gc.collect 회수 0, OOM 가드) 방출.
    # ref token pre-compute 재로드(~1s)는 종목 8개당 1회라 무시 가능. 전수(2928) 빌드 메모리 안전 필수
    # (free RAM 15GB 환경: workers 2 + per-child 8 권장 — 거대 금융지주 XML spike OOM 회피).
    with mp.Pool(processes=numWorkers, initializer=_initWorker, initargs=(refPathStr,), maxtasksperchild=8) as pool:
        for code, pcount, rowCount, _elapsed in pool.imap_unordered(_buildOne, args, chunksize=4):
            result[code] = (pcount, rowCount)
            processed += 1
            totalRows += rowCount
            if pcount == 0:
                failed += 1
            if verbose and processed % progressEvery == 0:
                wall = time.perf_counter() - t0
                rate = processed / wall if wall > 0 else 0
                eta = (len(codes) - processed) / rate if rate > 0 else 0
                _log.info(
                    "[%d/%d] %.1f code/s, ETA %.1f min, totalRows=%d, failed=%d",
                    processed,
                    len(codes),
                    rate,
                    eta / 60,
                    totalRows,
                    failed,
                )
    if verbose:
        wall = time.perf_counter() - t0
        _log.info("완료: %d codes, %d failed, %d totalRows, %.1f min", len(codes), failed, totalRows, wall / 60)
    return result


def _main() -> None:
    """CLI entry — ``python -X utf8 -m dartlab.providers.dart.panel.build --codes 005930``.

    Args:
        없음 (argparse).

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> _main()  # doctest: +SKIP
    """
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="panel artifact 빌드")
    ap.add_argument("--codes", type=str, default="", help="콤마구분 종목코드. 빈값=5 baseline")
    ap.add_argument("--ref", type=str, default=str(panelXbrlRefPath()), help="ref parquet (기본=패키지 동봉)")
    ap.add_argument("--out", type=str, default="data/dart/panel", help="출력 base dir")
    ap.add_argument("--all", action="store_true", help="전종목 빌드 (multiprocessing)")
    ap.add_argument("--spine", action="store_true", help="정부 서식 뼈대(spineData.py) 생성 — 기준 종목 1개")
    ap.add_argument(
        "--noteTaxonomy", action="store_true", help="주석 뼈대(noteTaxonomyData.py) 생성 — 전 corpus XBRL 학습"
    )
    ap.add_argument("--minFreq", type=int, default=3, help="noteTaxonomy 제목 총빈도 하한 (노이즈 컷)")
    ap.add_argument(
        "--dominanceRatio", type=float, default=0.8, help="noteTaxonomy 최빈코드 지배비율 하한 (모호제목 제외)"
    )
    ap.add_argument("--workers", type=int, default=8, help="Pool workers (OOM 가드: polars 힙 200~500MB/종목, ≤4 권장)")
    ap.add_argument("--rebuild", action="store_true", help="--all 시 이미 빌드된 종목도 재빌드 (기본=resumable skip)")
    args = ap.parse_args()

    refDf: pl.DataFrame | None = None
    refPath = Path(args.ref)
    if refPath.exists():
        refDf = pl.read_parquet(str(refPath))
        _log.info("ref table load: %s (%d entry)", refPath, refDf.height)

    if args.spine:
        from .spineBuilder import buildSpine

        # 기준 종목 1개 (정부 표준 서식이라 한 회사 reference 로 충분). 첫 --codes 또는 기본.
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        stats = buildSpine(codes[0] if codes else "005930", refDf=refDf, verbose=True)
        _log.info("=== spine 완료: code=%d, rows=%d ===", stats["code"], stats["rows"])
        return

    if args.noteTaxonomy:
        from .noteTaxonomy import buildAndWrite

        stats = buildAndWrite(verbose=True, minFreq=args.minFreq, dominanceRatio=args.dominanceRatio)
        _log.info(
            "=== noteTaxonomy 완료: entries=%d (minFreq=%d, dominanceRatio=%.2f) ===",
            stats["entries"],
            args.minFreq,
            args.dominanceRatio,
        )
        return

    if args.all:
        buildPanelAll(refPath=args.ref, outBaseDir=args.out, numWorkers=args.workers, skipExisting=not args.rebuild)
        return

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] or None
    out = buildPanelBaseline(codes=codes, refDf=refDf, verbose=True)
    total = sum(sum(p.values()) for p in out.values())
    _log.info("=== 완료 %d 종목, %d panel rows ===", len(out), total)


if __name__ == "__main__":
    _main()
