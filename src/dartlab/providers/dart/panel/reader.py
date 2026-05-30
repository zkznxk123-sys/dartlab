"""panel RUNTIME reader (L1 read) — panel parquet → lazy scan / long.

``Panel`` facade 가 wrap 하는 read backend. ``scan_parquet`` + columnar projection 만
사용 (lxml/zip import 0 — BUILD 와 물리 분리, R2). 콜드 <1s 핵심: 본문(contentRaw)은
show 시점 per-query materialize, meta board 는 contentRaw 제외로 <1MB.

LLM Specifications:
    AntiPatterns:
        - 옛 docs.parquet 호환 layer 신설 금지 — 신 panel artifact 만 backend.
        - in-memory 전체 누적 read 금지 — scan_parquet + columnar projection.
        - lxml / zipfile import 금지 — BUILD(gather) 전용(R2).
    OutputSchema:
        - ``scanPanel(code, ...) -> pl.LazyFrame | None``.
        - ``readLong(code, ...) -> pl.DataFrame | None`` (14-col long + disclosureKey).
    Prerequisites:
        - data/dart/panel/{code}/*.parquet (BUILD 결과).
        - data/bridge/panelBridge.parquet (disclosureKey fallback).
    Freshness:
        - panel parquet 변경 시 캐시 0 (매 호출 read).
    Dataflow:
        - panel *.parquet → polars scan → disclosureKey(이미 채워짐, 없으면 fallback).
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)


def _panelDir(code: str, marketNs: str = "kr") -> Path:
    """panel artifact read 디렉터리.

    Args:
        code: 종목코드(KR) 또는 CIK/ticker(US).
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        KR: ``data/dart/panel/{code}/`` · US: ``data/edgar/panel/{code}/``.

    Raises:
        없음.

    Example:
        >>> _panelDir("005930").as_posix().endswith("dart/panel/005930")  # doctest: +SKIP
        True

    SeeAlso:
        - ``scanPanel`` — 본 디렉터리 scan.
        - ``core.dataConfig`` — panel 경로 SSOT(S5).

    Requires:
        - dartlab.config.

    Capabilities:
        - 시장별 panel artifact 단일 경로 — reader 가 본 함수만 경유.

    Guide:
        - 내부 helper — scanPanel/readLong 경유.

    AIContext:
        - 경로 계산만.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지 — 본 함수 단일.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - (code, marketNs) → data/{dart|edgar}/panel/{code}.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "panel" / code


def scanPanel(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.LazyFrame | None:
    """panel artifact LazyFrame (collect 0 — show/pivot 가 per-query 필터).

    런타임 경량화 핵심: scan_parquet 만 반환. 호출자가 canonical 키 filter + 필요 컬럼만
    select → collect 시점에 해당 섹션 contentRaw 만 materialize (전체 본문 로드 회피).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 파일만 scan. None = 전체.

    Returns:
        LazyFrame 또는 None (artifact 없음).

    Raises:
        없음.

    Example:
        >>> lf = scanPanel("005930")  # doctest: +SKIP

    SeeAlso:
        - ``readLong`` — eager read + disclosureKey.
        - ``pivot.readPanelWide`` — 회사내 수평화.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - lazy scan → per-query filter/projection 으로 콜드 <1s, 메모리 최소.

    Guide:
        - cross-entity scan 또는 lazy 파이프라인에 사용.

    AIContext:
        - scan_parquet only — materialize 0.

    LLM Specifications:
        AntiPatterns:
            - read_parquet eager 금지(전체 본문 로드) — scan_parquet.
        OutputSchema:
            - ``pl.LazyFrame | None``.
        Prerequisites:
            - data/{dart|edgar}/panel/{code}/*.parquet.
        Freshness:
            - 매 호출 scan.
        Dataflow:
            - dir glob → (periods filter) → scan_parquet.
        TargetMarkets:
            - KR + US.
    """
    d = _panelDir(code, marketNs)
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if periods:
        files = [f for f in files if f.stem in set(periods)]
    if not files:
        return None
    return pl.scan_parquet([str(f) for f in files])


def readLong(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.DataFrame | None:
    """panel long format read + disclosureKey 부착(fallback).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace ("kr" / "us").
        periods: 특정 period 만. None = 전체.

    Returns:
        long DataFrame (14-col + disclosureKey) 또는 None (artifact 없음/빈).

    Raises:
        없음 — read 실패는 None.

    Example:
        >>> df = readLong("005930")  # doctest: +SKIP

    SeeAlso:
        - ``scanPanel`` — lazy 버전.
        - ``pivot.readPanelWide`` — wide 수평화.
        - ``core.panel.resolveBatch`` — disclosureKey fallback.

    Requires:
        - polars. panel artifact. (fallback 시) bridge parquet.

    Capabilities:
        - 한 회사 전(또는 일부) 기간 long 본문 read — disclosureKey 보장.

    Guide:
        - pivot/cross/facade 가 호출. 직접 호출 가능.

    AIContext:
        - build 가 채운 disclosureKey 사용, 옛 artifact(전부 null)만 fallback resolve.

    LLM Specifications:
        AntiPatterns:
            - 매 read 마다 resolveBatch 금지 — build 가 채운 값 우선, null 일 때만.
        OutputSchema:
            - ``pl.DataFrame | None`` (14-col + disclosureKey).
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 호출 read.
        Dataflow:
            - parquet read → disclosureKey null 검사 → (fallback) resolveBatch.
        TargetMarkets:
            - KR + US.
    """
    d = _panelDir(code, marketNs)
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if periods:
        files = [f for f in files if f.stem in set(periods)]
    if not files:
        return None
    try:
        df = pl.read_parquet([str(f) for f in files])
    except (pl.exceptions.PolarsError, OSError) as exc:
        _log.warning("panel read 실패 %s: %s", code, exc)
        return None
    if df.is_empty():
        return None
    if "disclosureKey" not in df.columns or df["disclosureKey"].null_count() == df.height:
        from dartlab.core.panel import resolveBatch

        if "disclosureKey" in df.columns:
            df = df.drop("disclosureKey")
        df = resolveBatch(df, marketNs=marketNs)
    return df
