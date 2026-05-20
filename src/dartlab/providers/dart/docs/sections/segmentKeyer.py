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
        textSemanticPathKey: str | None = None,
        headerHash: str | None = None,
    ) -> tuple[str, int, str]:
        """table block — `table|p:{path}|occ:{n}` (path-anchored, period-invariant).

        우선순위:
        1. notes topic + notesHeadingKey → `table|sem:{notesHeadingKey}`
        2. textSemanticPathKey 있음 → `table|p:{path}` + occurrence (같은 path 안 N-th table)
        3. headerHash fallback → `table|h:{hash}` (path 없는 leaf-only chapter 인 경우)
        4. sourceBlockOrder 최후 fallback

        path-anchored 정공법:
        - 같은 (topic, textSemanticPathKey) 안 N-th table 은 *모든 period 에서* 같은 segmentKey
        - DART 가 표 header 포맷을 시기별로 바꿔도 (예: "구분" vs "구 분") segmentKey 분리 안 됨
        - 옛 headerHash 룰의 fragility (header text 변형마다 hash 분리) 해결
        - 회귀 사례 (000660 companyOverview "연결대상회사의 변동내용" 표): 시기별로 5 개
          hash 로 분산되던 표가 1 개 segmentKey 로 정합 → wide-format 의 *1 개 row*
        """
        if isNotesTopic and notesHeadingKey:
            base = f"table|sem:{notesHeadingKey}"
        elif textSemanticPathKey:
            base = f"table|p:{textSemanticPathKey}"
        elif headerHash:
            base = f"table|h:{headerHash}"
        else:
            base = f"table|sb:{sourceBlockOrder}"
        return self._emit(topic, base)
