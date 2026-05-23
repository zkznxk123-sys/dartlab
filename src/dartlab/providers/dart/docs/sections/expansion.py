"""text/table block → heading state 누적 + segmentKey 부여.

``_expandStructuredRows(rows)`` 가 ``_reportRowsToTopicRows`` 결과 row 들을
순회하며:
- text block: ``parseTextStructureWithState`` 로 heading 계층 파싱 → node 별 row
- table block: 직전 heading state 의 textPath 상속 (commit 0f719c442)
- segmentKey 부여 — ``body|p:...`` / ``heading|...`` / ``table|sem:...`` /
  ``table|sb:...`` 4 룰. occurrence 카운터 per (topic, segmentKeyBase).

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수를 re-import.
"""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.providers.dart.docs.sections.segmentKeyer import SegmentKeyer
from dartlab.providers.dart.docs.sections.tableParser import tableHeaderHash
from dartlab.providers.dart.docs.sections.textStructure import parseTextStructureWithState

_NOTES_TOPICS = frozenset({"financialNotes", "consolidatedNotes"})


def _headingPathStrings(
    headings: list[dict[str, object]],
) -> tuple[list[str], list[str], list[str], str | None, str | None, str | None, str | None, str | None]:
    """heading stack → (labels, keys, semanticKeys, textPath, textPathKey,
    textParentPathKey, textSemanticPathKey, textSemanticParentPathKey).

    이전: 3 회 list comprehension + 5 회 ' > '.join. 본 helper 가 1 패스 + 5 join 으로
    축소. 200k rows × 5 stack items 핫 패스에서 단일 list iterate 로 메모리 +
    CPU 절약.
    """
    pathLabels: list[str] = []
    pathKeys: list[str] = []
    semanticPathKeys: list[str] = []
    for item in headings:
        pathLabels.append(str(item["label"]))
        k = str(item["key"])
        if k:
            pathKeys.append(k)
        sk = str(item.get("semanticKey") or "")
        if sk:
            semanticPathKeys.append(sk)
    textPath = " > ".join(pathLabels) if pathLabels else None
    textPathKey = " > ".join(pathKeys) if pathKeys else None
    textParentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
    textSemanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
    textSemanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
    return (
        pathLabels,
        pathKeys,
        semanticPathKeys,
        textPath,
        textPathKey,
        textParentPathKey,
        textSemanticPathKey,
        textSemanticParentPathKey,
    )


def _expandStructuredRows(rows: list[dict[str, object]]) -> Iterator[dict[str, object]]:
    """rows를 text structure로 확장하여 yield한다. occurrence는 SegmentKeyer 인라인 카운트."""
    headingStateByTopic: dict[str, list[dict[str, object]]] = {}
    keyer = SegmentKeyer()
    lastHeadingKeyByTopic: dict[str, str] = {}
    # topic 별 sticky promoteKorean — 한 번 한글 root 로 결정되면 후속 chunk 모두
    # 한글 root 유지. chunk-level promoteKorean 은 src=0 한글 → src=2 numeric →
    # src=4 한글 순서에서 src=2 의 numeric 이 root 로 박혀 src=4 의 한글이 sub 로
    # misattribute (LG 회귀). topic-level sticky 로 차단.
    promoteKoreanByTopic: dict[str, bool] = {}

    hasProjection = False
    for row in rows:
        if row.get("projectionKind") is not None:
            hasProjection = True
            break

    if hasProjection:
        orderedRows = sorted(
            rows,
            key=lambda r: (
                int(r.get("majorNum") or 99),
                int(r.get("orderSeq") or 999999),
                int(r.get("sourceBlockOrder") or r.get("blockOrder") or 0),
            ),
        )
    else:
        orderedRows = rows

    for row in orderedRows:
        rowGet = row.get  # local binding — dict.get attribute lookup 회피
        blockType = str(rowGet("blockType") or "text")
        topic = str(rowGet("topic") or "")
        sourceBlockOrder = int(rowGet("sourceBlockOrder") or rowGet("blockOrder") or 0)
        orderSeq = int(rowGet("orderSeq") or 0)
        baseRow = dict(row)
        baseRow["sourceBlockOrder"] = sourceBlockOrder

        if blockType != "text":
            currentHeadings = headingStateByTopic.get(topic, [])
            if currentHeadings:
                (_, _, _, textPath, textPathKey, textParentPathKey, textSemanticPathKey, textSemanticParentPathKey) = (
                    _headingPathStrings(currentHeadings)
                )
                lastLevel = currentHeadings[-1]["level"]
                baseRow["textLevel"] = int(lastLevel) if isinstance(lastLevel, (int, str)) else None
                baseRow["textPath"] = textPath
                baseRow["textPathKey"] = textPathKey
                baseRow["textParentPathKey"] = textParentPathKey
                baseRow["textSemanticPathKey"] = textSemanticPathKey
                baseRow["textSemanticParentPathKey"] = textSemanticParentPathKey
            else:
                baseRow["textLevel"] = None
                baseRow["textPath"] = None
                baseRow["textPathKey"] = None
                baseRow["textParentPathKey"] = None
                baseRow["textSemanticPathKey"] = None
                baseRow["textSemanticParentPathKey"] = None
            baseRow["textNodeType"] = "table"
            baseRow["textStructural"] = None
            baseRow["segmentOrder"] = 0
            lastKey = lastHeadingKeyByTopic.get(topic)
            # path-anchored segmentKey — 같은 path 안 N-th table 은 모든 period 에서 같은 segmentKey.
            # 옛 headerHash 룰 fallback 유지 (path 없는 chapter-leaf 표 등 edge case).
            tableText = str(rowGet("text") or "")
            headerHash = tableHeaderHash(tableText) if tableText else None
            tablePathKey = baseRow.get("textSemanticPathKey") or baseRow.get("textPathKey")
            segmentKeyBase, occurrence, segmentKey = keyer.forTableBlock(
                topic,
                sourceBlockOrder=sourceBlockOrder,
                notesHeadingKey=lastKey,
                isNotesTopic=topic in _NOTES_TOPICS,
                textSemanticPathKey=str(tablePathKey) if isinstance(tablePathKey, str) and tablePathKey else None,
                headerHash=headerHash,
            )
            baseRow["segmentKeyBase"] = segmentKeyBase
            baseRow["sortOrder"] = orderSeq * 1000
            baseRow["segmentOccurrence"] = occurrence
            baseRow["segmentKey"] = segmentKey
            yield baseRow
            continue

        text = str(rowGet("text") or "").strip()
        initialHeadings = headingStateByTopic.get(topic, [])
        stickyPromote = promoteKoreanByTopic.get(topic)
        nodes, finalHeadings, chunkPromoteKorean = parseTextStructureWithState(
            text,
            sourceBlockOrder=sourceBlockOrder,
            topic=topic,
            initialHeadings=initialHeadings,
            promoteKorean=stickyPromote,
        )
        # 한 번 True 로 결정되면 sticky — topic 의 후속 chunk 모두 한글 root 유지.
        if chunkPromoteKorean and not stickyPromote:
            promoteKoreanByTopic[topic] = True
        headingStateByTopic[topic] = finalHeadings
        if topic in _NOTES_TOPICS and finalHeadings:
            lastLabel = str(finalHeadings[-1].get("label") or "")
            lastSemKey = str(finalHeadings[-1].get("semanticKey") or finalHeadings[-1].get("key") or lastLabel)
            if lastSemKey:
                lastHeadingKeyByTopic[topic] = lastSemKey
        if not nodes:
            baseRow["textNodeType"] = "body"
            baseRow["textStructural"] = True
            if finalHeadings:
                (_, _, _, textPath, textPathKey, textParentPathKey, textSemanticPathKey, textSemanticParentPathKey) = (
                    _headingPathStrings(finalHeadings)
                )
                textLevel = int(finalHeadings[-1]["level"])
                segmentKeyBase, occurrence, segmentKey = keyer.forTextBody(
                    topic, textLevel=textLevel, textSemanticPathKey=textSemanticPathKey
                )
            else:
                textLevel = 0
                textPath = None
                textPathKey = None
                textParentPathKey = None
                textSemanticPathKey = None
                textSemanticParentPathKey = None
                segmentKeyBase, occurrence, segmentKey = keyer.forTextNoHeading(topic)
            baseRow["textLevel"] = textLevel
            baseRow["textPath"] = textPath
            baseRow["textPathKey"] = textPathKey
            baseRow["textParentPathKey"] = textParentPathKey
            baseRow["textSemanticPathKey"] = textSemanticPathKey
            baseRow["textSemanticParentPathKey"] = textSemanticParentPathKey
            baseRow["segmentOrder"] = 0
            baseRow["segmentKeyBase"] = segmentKeyBase
            baseRow["sortOrder"] = orderSeq * 1000
            baseRow["segmentOccurrence"] = occurrence
            baseRow["segmentKey"] = segmentKey
            yield baseRow
            continue

        for node in nodes:
            nodeRow = dict(baseRow)
            nodeRow["text"] = str(node["text"])
            nodeRow["textNodeType"] = node["textNodeType"]
            nodeRow["textStructural"] = bool(node.get("textStructural", True))
            nodeRow["textLevel"] = node["textLevel"]
            nodeRow["textPath"] = node["textPath"]
            nodeRow["textPathKey"] = node["textPathKey"]
            nodeRow["textParentPathKey"] = node["textParentPathKey"]
            nodeRow["textSemanticPathKey"] = node.get("textSemanticPathKey")
            nodeRow["textSemanticParentPathKey"] = node.get("textSemanticParentPathKey")
            nodeRow["segmentOrder"] = node["segmentOrder"]
            segmentKeyBase, occurrence, segmentKey = keyer.forTextHeadingNode(topic, str(node["segmentKeyBase"]))
            nodeRow["segmentKeyBase"] = segmentKeyBase
            nodeRow["sortOrder"] = (orderSeq * 1000) + int(node["segmentOrder"])
            nodeRow["segmentOccurrence"] = occurrence
            nodeRow["segmentKey"] = segmentKey
            yield nodeRow
