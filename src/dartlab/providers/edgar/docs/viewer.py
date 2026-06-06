"""EDGAR viewer — plan delegated-prancing-tower PR-E5.

DART viewer 의 ``_buildTextBlock`` / ``_buildTableBlock`` / ``viewerTextDocument`` /
``serialize*`` 헬퍼를 그대로 재사용. EDGAR 내부 docs wide schema 가
DART 와 동일 (``topic / blockType / blockOrder / textNodeType / textLevel / textPath +
period 컬럼``) 이므로 block builder 가 source-agnostic.

미지원 (EDGAR scope 외):
- finance topic block (``_buildFinanceBlock``) — EDGAR finance 는 XBRL companyfacts 가
  SSOT 라 viewer 본문 path 외.
- report block (``_buildReportBlock``) — EDGAR 는 SEC 본문 자체가 sections 와 일치, 별도 report dataset 없음.

진입점:
- ``viewerBlocks(company, topic)`` — text + table block list
- ``viewerTextDocument(topic, blocks)`` — interleaved document (DART 의 동치)
- ``serializeViewerBlock(block)`` — JSON 직렬화 (re-export)
- ``serializeViewerTextDocument(doc)`` — JSON 직렬화 (re-export)
"""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.viewer import (
    ViewerBlock,
    _buildTextBlock,  # noqa: E402  (helper 재사용)
    _periodCols,
)
from dartlab.providers.dart.viewer import (
    viewerTextDocument as _dartViewerTextDocument,
)
from dartlab.providers.dart.viewerSerialize import (
    serializeViewerBlock,
    serializeViewerTextDocument,
)
from dartlab.providers.dart.viewerTable import _buildTableBlock

__all__ = [
    "ViewerBlock",
    "viewerBlocks",
    "viewerTextDocument",
    "serializeViewerBlock",
    "serializeViewerTextDocument",
]


def viewerBlocks(company, topic: str) -> list[ViewerBlock]:
    """EDGAR 내부 docs wide 위에서 topic 의 block 리스트 빌드.

    DART 의 동치 함수의 축소판 — finance / report block path 제외. EDGAR sections
    artifact 의 text / table row 만 viewer 대상.

    Args:
        company: EDGAR ``Company`` 인스턴스 (``_docs.sections`` 내부 wide accessor 보유).
        topic: 검색 topic (예 ``"10-K::item7Mdna"``).

    Returns:
        block list — text + table block. topic 부재 시 빈 list.

    Raises:
        없음.

    Example:
        >>> blocks = viewerBlocks(Company("AAPL"), "10-K::item7Mdna")  # doctest: +SKIP
    """
    sec = company._docs.sections
    if sec is None or sec.is_empty():
        return []
    topicFrame = sec.filter(pl.col("topic") == topic)
    if topicFrame.is_empty():
        return []
    if "blockOrder" not in topicFrame.columns:
        return []
    periodCols = _periodCols(topicFrame)
    blockOrders = topicFrame["blockOrder"].unique().sort().to_list()
    blocks: list[ViewerBlock] = []
    for bo in blockOrders:
        boRows = topicFrame.filter(pl.col("blockOrder") == bo)
        bt = boRows["blockType"][0] if "blockType" in boRows.columns else "text"
        if bt == "text":
            blk = _buildTextBlock(boRows, bo, periodCols)
        elif bt == "table":
            blk = _buildTableBlock(company, topic, topicFrame, bo, periodCols)
        else:
            blk = None
        if blk:
            blocks.append(blk)
    return blocks


def viewerTextDocument(topic: str, blocks: list[ViewerBlock]):
    """DART viewer 의 ``viewerTextDocument`` 재사용 — block list 가 schema 동일.

    Args:
        topic: 검색 topic.
        blocks: ``viewerBlocks`` 결과.

    Returns:
        ``ViewerTextDocument`` 또는 None.

    Raises:
        없음.

    Example:
        >>> doc = viewerTextDocument("10-K::item7Mdna", blocks)  # doctest: +SKIP
    """
    return _dartViewerTextDocument(topic, blocks)
