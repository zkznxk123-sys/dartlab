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
from dartlab.core.panel import canonicalKeyExpr

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

    When:
        - 전종목 빌드 후 cross-entity 가속 index 가 필요할 때.

    How:
        - {code}/*.parquet scan → locator projection → _index.parquet write.

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


def labelPath(marketNs: str = "kr") -> Path:
    """canonicalKey → 한글 표시라벨 테이블 경로 (_label.parquet).

    Args:
        marketNs: 시장 namespace ("kr"/"us").

    Returns:
        ``data/{dart|edgar}/panel/_label.parquet`` Path (_index 와 동거, nested 업로드 포함).

    Raises:
        없음.

    Example:
        >>> labelPath().name
        '_label.parquet'

    SeeAlso:
        - ``buildLabel`` — 본 경로 write.
        - ``providers.dart.panel.reader`` — 본 경로 read(show byLabel).

    Requires:
        - dartlab.config.

    Capabilities:
        - 표시라벨 단일 경로 SSOT — gather build·providers read 공유.

    Guide:
        - show byLabel 이 존재 확인 후 read.

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
            - marketNs → data/{dart|edgar}/panel/_label.parquet.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "panel" / "_label.parquet"


def buildLabel(
    *,
    marketNs: str = "kr",
    refPath: Path | str | None = None,
    outPath: Path | str | None = None,
    verbose: bool = True,
) -> dict:
    """panelXbrlRef → canonicalKey 별 대표 한글 라벨 (_label.parquet). 큐레이션 0.

    표시 전용 보강 — 정렬은 canonicalKey 가 책임(라벨은 UX). ref 의 (rawId→canonicalKey,
    rawTitleCanonical, corpCount) 에서 canonicalKey 별 corpCount 최빈 제목을 대표 라벨로 선정
    (회사들이 실제 쓰는 제목 = 라벨, 손 큐레이션 0). 라벨 부정확해도 정렬 무영향.

    Args:
        marketNs: 시장 namespace (기본 "kr").
        refPath: panelXbrlRef 경로. None = panelXbrlRefPath().
        outPath: 출력 경로. None = labelPath(marketNs).
        verbose: 진행 로그.

    Returns:
        통계 dict — ``{rowCount, path}``. ref 없으면 rowCount 0.

    Raises:
        없음 — ref 부재 시 빈 결과.

    Example:
        >>> buildLabel(marketNs="kr")  # doctest: +SKIP
        {'rowCount': 312, 'path': 'data/dart/panel/_label.parquet'}

    SeeAlso:
        - ``canonicalKeyExpr`` — rawId → canonicalKey.
        - ``providers.dart.panel.Panel.show`` — 본 라벨로 byLabel 검색.
        - ``panelXbrlRefPath`` — 입력 ref.

    Requires:
        - polars. core.panel.canonicalKeyExpr. panelXbrlRef.

    Capabilities:
        - canonicalKey 의 한글 표시라벨을 corpus 에서 파생 — show("재고") substring 검색 지원.

    Guide:
        - refScan/build 후 syncPanel 에서 호출. ref 갱신 시 재생성(idempotent).

    AIContext:
        - 표시 전용 — 정렬 비핵심. 손 큐레이션 0(corpus 최빈 제목).

    When:
        - canonicalKey 의 사람용 표시라벨이 필요할 때 (refScan 후).

    How:
        - ref filter(marketNs·제목) → canonicalKeyExpr(rawId) → corpCount 최빈 제목 → write.

    LLM Specifications:
        AntiPatterns:
            - 손수 라벨 큐레이션 금지 — corpus rawTitleCanonical 최빈.
            - 라벨을 정렬키로 사용 금지 — 정렬은 canonicalKey, 라벨은 표시.
        OutputSchema:
            - ``dict`` (rowCount/path) + _label.parquet (canonicalKey/labelKr 2-col).
        Prerequisites:
            - panelXbrlRef (refScan 산출).
        Freshness:
            - ref 갱신 시 재생성.
        Dataflow:
            - ref → canonicalKeyExpr → group_by(canonicalKey) 최빈 제목 → _label.parquet.
        TargetMarkets:
            - KR (DART). US 후속.
    """
    refP = Path(refPath) if refPath is not None else panelXbrlRefPath()
    out = Path(outPath) if outPath is not None else labelPath(marketNs)
    if not refP.exists():
        _log.warning("panelXbrlRef 없음: %s", refP)
        return {"rowCount": 0, "path": str(out)}

    ref = pl.read_parquet(str(refP))
    if "marketNs" in ref.columns:
        ref = ref.filter(pl.col("marketNs") == marketNs)
    ref = ref.filter(pl.col("rawTitleCanonical").is_not_null() & (pl.col("rawTitleCanonical").str.len_chars() > 0))
    ref = ref.with_columns(canonicalKeyExpr("rawId")).filter(pl.col("canonicalKey").is_not_null())
    if ref.is_empty():
        return {"rowCount": 0, "path": str(out)}

    label = (
        ref.sort("corpCount", descending=True)
        .group_by("canonicalKey", maintain_order=True)
        .agg(pl.col("rawTitleCanonical").first().alias("labelKr"))
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    label.write_parquet(str(out), compression="zstd")
    if verbose:
        _log.info("buildLabel: %d canonicalKey → %s", label.height, out)
    return {"rowCount": label.height, "path": str(out)}


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
