"""panel 회사내 수평화 (L1 read) — long → wide pivot (항목 × period).

``readLong`` 결과를 ``anchorLatest`` 로 최신기준 정렬한 뒤 period 축으로 pivot → 한 회사
다기간이 한 행에 가로 정렬(회사내 수평화). meta board 는 contentRaw 제외(<1MB, 콜드 <1s).

LLM Specifications:
    AntiPatterns:
        - pivot index 에 xbrlClass 유지 금지 — era drift(scope 로 대체, anchorLatest).
        - 다중 블록 contentRaw first 집계 금지 — blockOrder 순 join(무손실).
        - lxml/network import 금지(R2).
    OutputSchema:
        - ``readPanelWide(code, ..., valueColumn) -> pl.DataFrame | None`` (index=canonical, col=period).
        - ``readMeta(code, ...) -> pl.DataFrame | None`` (blockOrder presence board, contentRaw 제외).
    Prerequisites:
        - polars. panel artifact (reader.readLong).
    Freshness:
        - 매 호출 read/pivot.
    Dataflow:
        - readLong → anchorLatest → (collapse) → pivot(period).
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.
"""

from __future__ import annotations

import logging

import polars as pl

from .anchor import anchorLatest
from .reader import readLong

_log = logging.getLogger(__name__)

_INDEX_COLS = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"]


def readPanelWide(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
    valueColumn: str = "contentRaw",
) -> pl.DataFrame | None:
    """panel wide pivot — index=(canonical key), columns=period (회사내 수평화).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 만. None = 전체.
        valueColumn: pivot cell 값 컬럼 (기본 "contentRaw" = 태그 raw XML).

    Returns:
        wide DataFrame. row identity = (chapter, sectionLeaf, blockLeaf, disclosureKey,
        scope). 또는 None (artifact 없음/빈).

    Raises:
        없음 — pivot 실패는 None.

    Example:
        >>> readPanelWide("005930", valueColumn="blockOrder")  # doctest: +SKIP

    SeeAlso:
        - ``reader.readLong`` — long 입력.
        - ``anchor.anchorLatest`` — 최신기준 정렬.
        - ``readMeta`` — contentRaw 제외 cheap board.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - 한 회사 다기간을 항목 행 × period 열로 정렬 — era drift 흡수(G2).

    Guide:
        - Panel facade 가 show/board 에 사용. 직접 호출 가능.

    AIContext:
        - contentRaw 는 join(무손실), 그 외 first. anchorLatest 후 pivot.

    When:
        - 한 회사 다기간을 항목 × period 로 수평화할 때.

    How:
        - readLong → anchorLatest → group collapse → period pivot.

    LLM Specifications:
        AntiPatterns:
            - contentRaw 다중블록 first 금지 — blockOrder 순 join.
            - xbrlClass pivot index 금지 — scope 대체.
        OutputSchema:
            - ``pl.DataFrame | None`` (index cols + period 열).
        Prerequisites:
            - panel artifact + period 컬럼.
        Freshness:
            - 매 호출.
        Dataflow:
            - readLong → anchorLatest → group(index,period) collapse → pivot.
        TargetMarkets:
            - KR + US.
    """
    long = readLong(code, marketNs=marketNs, periods=periods)
    if long is None or long.is_empty() or valueColumn not in long.columns:
        return None
    long = anchorLatest(long)
    indexCols = [c for c in _INDEX_COLS if c in long.columns]
    if not indexCols or "period" not in long.columns:
        return None
    aggExpr = pl.col("contentRaw").str.join("") if valueColumn == "contentRaw" else pl.col(valueColumn).first()
    try:
        collapsed = (
            long.sort("blockOrder")
            .group_by([*indexCols, "period"], maintain_order=True)
            .agg(aggExpr.alias(valueColumn))
        )
        return collapsed.pivot(values=valueColumn, index=indexCols, on="period", aggregate_function="first")
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("panel pivot 실패 %s: %s", code, exc)
        return None


def readMeta(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.DataFrame | None:
    """panel 구조 board (contentRaw 제외) — canonical 키 × period presence (콜드 <1s).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 만.

    Returns:
        wide meta board (cell = blockOrder = presence) 또는 None. contentRaw 디코드 0 → <1MB.

    Raises:
        없음.

    Example:
        >>> readMeta("005930")  # doctest: +SKIP

    SeeAlso:
        - ``readPanelWide`` — 본문 포함 wide.
        - ``Panel.board`` — 본 board 의 facade.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - 어떤 disclosure 가 어느 기간에 있는지 cheap 조회 — 본문은 show 시점 pull.

    Guide:
        - Panel 기본 board (콜드 <1s).

    AIContext:
        - blockOrder presence — footprint 최소.

    LLM Specifications:
        AntiPatterns:
            - contentRaw 포함 금지 — board 는 presence 만.
        OutputSchema:
            - ``pl.DataFrame | None`` (blockOrder board).
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 호출.
        Dataflow:
            - readPanelWide(valueColumn="blockOrder").
        TargetMarkets:
            - KR + US.
    """
    return readPanelWide(code, marketNs=marketNs, periods=periods, valueColumn="blockOrder")
