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

from dartlab.providers.dart.docs.sections.textStructure import parseTextStructureWithState

_NOTES_TOPICS = frozenset({"financialNotes", "consolidatedNotes"})


def _expandStructuredRows(rows: list[dict[str, object]]) -> Iterator[dict[str, object]]:
    """rows를 text structure로 확장하여 yield한다. occurrence는 인라인 카운트."""
    headingStateByTopic: dict[str, list[dict[str, object]]] = {}
    occurrenceCount: dict[tuple[str, str], int] = {}
    lastHeadingKeyByTopic: dict[str, str] = {}

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
        blockType = str(row.get("blockType") or "text")
        topic = str(row.get("topic") or "")
        sourceBlockOrder = int(row.get("sourceBlockOrder") or row.get("blockOrder") or 0)
        orderSeq = int(row.get("orderSeq") or 0)
        baseRow = dict(row)
        baseRow["sourceBlockOrder"] = sourceBlockOrder

        if blockType != "text":
            currentHeadings = headingStateByTopic.get(topic, [])
            if currentHeadings:
                pathLabels = [str(item["label"]) for item in currentHeadings]
                pathKeys = [str(item["key"]) for item in currentHeadings if str(item["key"])]
                semanticPathKeys = [
                    str(item["semanticKey"]) for item in currentHeadings if str(item.get("semanticKey"))
                ]
                lastLevel = currentHeadings[-1]["level"]
                baseRow["textLevel"] = int(lastLevel) if isinstance(lastLevel, (int, str)) else None
                baseRow["textPath"] = " > ".join(pathLabels) if pathLabels else None
                baseRow["textPathKey"] = " > ".join(pathKeys) if pathKeys else None
                baseRow["textParentPathKey"] = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
                baseRow["textSemanticPathKey"] = " > ".join(semanticPathKeys) if semanticPathKeys else None
                baseRow["textSemanticParentPathKey"] = (
                    " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
                )
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
            if topic in _NOTES_TOPICS and lastKey:
                segmentKeyBase = f"table|sem:{lastKey}"
            else:
                segmentKeyBase = f"table|sb:{sourceBlockOrder}"
            baseRow["segmentKeyBase"] = segmentKeyBase
            baseRow["sortOrder"] = orderSeq * 1000
            occKey = (topic, segmentKeyBase)
            occurrenceCount[occKey] = occurrenceCount.get(occKey, 0) + 1
            baseRow["segmentOccurrence"] = occurrenceCount[occKey]
            baseRow["segmentKey"] = f"{segmentKeyBase}|occ:{occurrenceCount[occKey]}"
            yield baseRow
            continue

        text = str(row.get("text") or "").strip()
        initialHeadings = headingStateByTopic.get(topic, [])
        nodes, finalHeadings = parseTextStructureWithState(
            text,
            sourceBlockOrder=sourceBlockOrder,
            topic=topic,
            initialHeadings=initialHeadings,
        )
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
                pathLabels = [str(item["label"]) for item in finalHeadings]
                pathKeys = [str(item["key"]) for item in finalHeadings if str(item["key"])]
                semanticPathKeys = [str(item["semanticKey"]) for item in finalHeadings if str(item["semanticKey"])]
                textLevel = int(finalHeadings[-1]["level"])
                textPath = " > ".join(pathLabels) if pathLabels else None
                textPathKey = " > ".join(pathKeys) if pathKeys else None
                textParentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
                textSemanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
                textSemanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
                segmentKeyBase = (
                    f"body|p:{textSemanticPathKey}" if textSemanticPathKey else f"body|lv:{textLevel}|a:empty"
                )
            else:
                textLevel = 0
                textPath = None
                textPathKey = None
                textParentPathKey = None
                textSemanticPathKey = None
                textSemanticParentPathKey = None
                segmentKeyBase = "body|lv:0|a:empty"
            baseRow["textLevel"] = textLevel
            baseRow["textPath"] = textPath
            baseRow["textPathKey"] = textPathKey
            baseRow["textParentPathKey"] = textParentPathKey
            baseRow["textSemanticPathKey"] = textSemanticPathKey
            baseRow["textSemanticParentPathKey"] = textSemanticParentPathKey
            baseRow["segmentOrder"] = 0
            baseRow["segmentKeyBase"] = segmentKeyBase
            baseRow["sortOrder"] = orderSeq * 1000
            occKey = (topic, segmentKeyBase)
            occurrenceCount[occKey] = occurrenceCount.get(occKey, 0) + 1
            baseRow["segmentOccurrence"] = occurrenceCount[occKey]
            baseRow["segmentKey"] = f"{segmentKeyBase}|occ:{occurrenceCount[occKey]}"
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
            segmentKeyBase = node["segmentKeyBase"]
            nodeRow["segmentKeyBase"] = segmentKeyBase
            nodeRow["sortOrder"] = (orderSeq * 1000) + int(node["segmentOrder"])
            occKey = (topic, str(segmentKeyBase))
            occurrenceCount[occKey] = occurrenceCount.get(occKey, 0) + 1
            nodeRow["segmentOccurrence"] = occurrenceCount[occKey]
            nodeRow["segmentKey"] = f"{segmentKeyBase}|occ:{occurrenceCount[occKey]}"
            yield nodeRow
