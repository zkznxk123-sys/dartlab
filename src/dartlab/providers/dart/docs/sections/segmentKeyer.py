"""segmentKey 부여 SSOT — 4 카테고리 (text body / heading / table notes / table non-notes).

기존: ``expansion.py`` 안 literal 문자열 4 곳 (``body|p:...`` / ``body|lv:0|a:empty``
/ ``table|sem:...`` / ``table|sb:...``) + occurrence 카운터가 함수 본문에 흩어져
schema 명시 안 됨. ``SegmentKeyer`` 가 단일 클래스로 모음 (operation.sectionsRefactor
§4-3 부채 3).

caller API 0 변경 — 결과 segmentKey 문자열 형식 동일. parity test 가드.
"""

from __future__ import annotations


class SegmentKeyer:
    """topic 단위 occurrence 카운터 + segmentKey 4 카테고리 생성.

    state: ``(topic, segmentKeyBase)`` → occurrence count. 호출 순서가 occurrence
    번호를 결정하므로 caller 가 row 순서를 보장해야 한다.

    Example:
        >>> keyer = SegmentKeyer()
        >>> keyer.forTableBlock(topic="financialNotes", sourceBlockOrder=12, notesHeadingKey="자본금")
        ('table|sem:자본금', 1, 'table|sem:자본금|occ:1')
    """

    __slots__ = ("_occurrenceCount",)

    def __init__(self) -> None:
        self._occurrenceCount: dict[tuple[str, str], int] = {}

    def _emit(self, topic: str, base: str) -> tuple[str, int, str]:
        key = (topic, base)
        self._occurrenceCount[key] = self._occurrenceCount.get(key, 0) + 1
        occurrence = self._occurrenceCount[key]
        return base, occurrence, f"{base}|occ:{occurrence}"

    def forTextNoHeading(self, topic: str) -> tuple[str, int, str]:
        """heading 없는 body block — ``body|lv:0|a:empty``."""
        return self._emit(topic, "body|lv:0|a:empty")

    def forTextBody(self, topic: str, *, textLevel: int, textSemanticPathKey: str | None) -> tuple[str, int, str]:
        """heading 아래 body block — ``body|p:{semanticPath}`` 또는 ``body|lv:{n}|a:empty``."""
        if textSemanticPathKey:
            base = f"body|p:{textSemanticPathKey}"
        else:
            base = f"body|lv:{textLevel}|a:empty"
        return self._emit(topic, base)

    def forTextHeadingNode(self, topic: str, segmentKeyBase: str) -> tuple[str, int, str]:
        """heading node — base 는 ``textStructure.parseTextStructureWithState`` 가 부여."""
        return self._emit(topic, segmentKeyBase)

    def forTableBlock(
        self,
        topic: str,
        *,
        sourceBlockOrder: int,
        notesHeadingKey: str | None,
        isNotesTopic: bool,
    ) -> tuple[str, int, str]:
        """table block — notes topic + heading 키 보유 시 ``table|sem:{key}``, 그 외 ``table|sb:{sb}``."""
        if isNotesTopic and notesHeadingKey:
            base = f"table|sem:{notesHeadingKey}"
        else:
            base = f"table|sb:{sourceBlockOrder}"
        return self._emit(topic, base)
