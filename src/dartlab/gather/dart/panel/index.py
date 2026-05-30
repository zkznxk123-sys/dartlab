"""panel slim 글로벌 인덱스 빌드 (L1 gather) — cross-entity 가속 (G6).

전 회사 panel artifact 에서 **locator 만**(corp/disclosureKey/xbrlClass/period/rceptNo/
blockOrder) 추출 → ``data/dart/panel/_index.parquet`` 단일 slim 테이블. contentRaw 제외
(scan_parquet columnar projection 으로 본문 미read → 빠름·경량). 회사간/세계마켓간 read 가
이 index 1회 스캔으로 "어느 회사·기간에 disclosure 있나" 식별 → 필요 cell 만 lazy pull
(100+ 회사 풀로드 회피).

scope 는 저장 안 함 — read 시점 xbrlClass 파생(R3, providers anchor.scopeExpr). index 는
raw 14-col 부분집합만 보관.

LLM Specifications:
    AntiPatterns:
        - contentRaw / scope / content_plain 저장 금지 — locator(raw 부분집합)만(R3·R4).
        - read_parquet eager 금지 — scan_parquet + columnar projection(본문 미read).
        - providers import 금지(gather↛providers, R1).
    OutputSchema:
        - ``buildIndex(...) -> dict`` (rowCount/codeCount/path 통계).
        - 출력: ``data/dart/panel/_index.parquet`` (7-col locator).
    Prerequisites:
        - polars. data/dart/panel/{code}/*.parquet (P4 전종목 빌드 후).
    Freshness:
        - 빌드 변경 시 재빌드 (changed code 만 가능).
    Dataflow:
        - {code}/*.parquet scan → locator projection → collect → _index.parquet write.
    TargetMarkets:
        - KR (DART) + US (EDGAR, marketNs 별 index).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# slim index locator 컬럼 (contentRaw·scope 제외 — R3/R4).
_INDEX_COLS = ["corp", "disclosureKey", "xbrlClass", "period", "rceptNo", "blockOrder"]


def buildIndex(
    *,
    marketNs: str = "kr",
    panelBaseDir: Path | str | None = None,
    outPath: Path | str | None = None,
    verbose: bool = True,
) -> dict:
    """전 회사 panel artifact → slim 글로벌 인덱스 (_index.parquet).

    Args:
        marketNs: 시장 namespace ("kr" → data/dart/panel, "us" → data/edgar/panel).
        panelBaseDir: panel base dir. None = config default.
        outPath: 출력 경로. None = ``{base}/_index.parquet``.
        verbose: 진행 로그.

    Returns:
        통계 dict — ``{rowCount, codeCount, path}``. artifact 없으면 rowCount 0.

    Raises:
        없음 — read 실패 회사는 skip.

    Example:
        >>> buildIndex(marketNs="kr")  # doctest: +SKIP
        {'rowCount': 412033, 'codeCount': 2928, 'path': 'data/dart/panel/_index.parquet'}

    SeeAlso:
        - ``build.buildPanelAll`` — 본 index 의 입력(panel artifact) 생산.
        - ``providers.dart.panel.crossCompany`` — index 활용 cross-entity read.

    Requires:
        - polars. 전종목 panel artifact.

    Capabilities:
        - cross-entity 가속(G6) — disclosure 의 (corp, period) locator 를 본문 없이 1테이블.

    Guide:
        - P4 전종목 빌드 후 / syncPanel 에서 호출. changed code 만 재빌드 가능.

    AIContext:
        - scan_parquet columnar projection — contentRaw 미read(슬림·고속).

    LLM Specifications:
        AntiPatterns:
            - contentRaw 포함 금지 — locator 만.
            - 전 파일 eager read 금지 — scan + projection.
        OutputSchema:
            - ``dict`` (rowCount/codeCount/path) + _index.parquet.
        Prerequisites:
            - panel artifact (P4).
        Freshness:
            - 빌드 변경 시.
        Dataflow:
            - {code}/*.parquet scan → _INDEX_COLS projection → marketNs lit → write.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    if panelBaseDir is None:
        panelBaseDir = Path(_cfg.dataDir) / base / "panel"
    panelBaseDir = Path(panelBaseDir)
    if outPath is None:
        outPath = panelBaseDir / "_index.parquet"
    outPath = Path(outPath)

    files = sorted(p for p in panelBaseDir.glob("*/*.parquet") if p.name != "_index.parquet")
    codes = {p.parent.name for p in files}
    if not files:
        _log.warning("panel artifact 없음: %s", panelBaseDir)
        return {"rowCount": 0, "codeCount": 0, "path": str(outPath)}

    if verbose:
        _log.info("buildIndex: %d 파일 / %d 종목 scan", len(files), len(codes))

    lf = pl.scan_parquet([str(f) for f in files]).select(_INDEX_COLS)
    idx = lf.with_columns(pl.lit(marketNs).alias("marketNs")).collect()
    outPath.parent.mkdir(parents=True, exist_ok=True)
    idx.write_parquet(str(outPath), compression="zstd")

    if verbose:
        _log.info("완료: %d row → %s", idx.height, outPath)
    return {"rowCount": idx.height, "codeCount": len(codes), "path": str(outPath)}


def indexPath(marketNs: str = "kr") -> Path:
    """slim 인덱스 경로 반환.

    Args:
        marketNs: 시장 namespace ("kr"/"us").

    Returns:
        ``data/{dart|edgar}/panel/_index.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> indexPath().name
        '_index.parquet'

    SeeAlso:
        - ``buildIndex`` — 본 경로 write.
        - ``providers.dart.panel.crossCompany`` — 본 경로 read.

    Requires:
        - dartlab.config.

    Capabilities:
        - index 단일 경로 SSOT — gather build·providers read 공유.

    Guide:
        - cross read 가 존재 확인 후 scan.

    AIContext:
        - 경로 계산만.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - marketNs → data/{dart|edgar}/panel/_index.parquet.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "panel" / "_index.parquet"


def panelXbrlRefPath() -> Path:
    """panelXbrlRef ref table 경로 — refScan 산출 + build/learn 입력 SSOT.

    Args:
        없음.

    Returns:
        ``data/dart/panelXbrlRef.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> panelXbrlRefPath().name
        'panelXbrlRef.parquet'

    SeeAlso:
        - ``build.refScan.scanAllZips`` — 본 경로 생산.
        - ``learn.learnBridge`` — 본 ref 로 학습.
        - ``build.buildPanelAll`` — 본 ref 로 fuzzy 매칭.

    Requires:
        - dartlab.config.

    Capabilities:
        - ref truth(S4) 단일 경로 — refScan write·build/learn read 공유.

    Guide:
        - refScan 후 build/learn 이 본 경로 참조.

    AIContext:
        - 경로 계산만.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - config.dataDir → data/dart/panelXbrlRef.parquet.
        TargetMarkets:
            - KR (DART).
    """
    return Path(_cfg.dataDir) / "dart" / "panelXbrlRef.parquet"
