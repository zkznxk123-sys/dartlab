"""TopicMapper — TOPIC_KEYWORDS 읽기 전용 래퍼.

기존 topicGraph.py의 TOPIC_KEYWORDS(33 topics)를
MapperEngine 인터페이스로 래핑한다. 원본 코드 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mappers.engine import BaseMapper, MapperStats


class TopicMapper(BaseMapper):
    """TOPIC_KEYWORDS (33 topics → 한국어 키워드) 래퍼."""

    @property
    def name(self) -> str:
        """name — TODO 한국어 동작 설명."""
        return "topic"

    def _keywords(self) -> dict[str, list[str]]:
        from dartlab.core.docs.topicGraph import TOPIC_KEYWORDS

        return TOPIC_KEYWORDS

    def lookup(self, key: str) -> dict | None:
        """topic 이름으로 키워드 목록 조회.

        영문 topic key 또는 한국어 키워드 역방향 조회.
        """
        kw = self._keywords()

        # 영문 topic key → 키워드 목록
        if key in kw:
            return {"topic": key, "keywords": kw[key]}

        # 한국어 키워드 → 해당 topic 역방향 검색
        for topic, words in kw.items():
            if key in words:
                return {"topic": topic, "keywords": words, "matchedBy": key}

        return None

    def stats(self) -> MapperStats:
        """stats — TODO 한국어 동작 설명."""
        kw = self._keywords()
        total_keywords = sum(len(v) for v in kw.values())
        return MapperStats(
            name=self.name,
            totalEntries=len(kw),
            mappedEntries=len(kw),
            coverage=1.0,
            lastUpdated="",
        )

    def allKeys(self) -> list[str]:
        """allKeys — TODO 한국어 동작 설명."""
        return list(self._keywords().keys())

    def topicForKeyword(self, keyword: str) -> str | None:
        """한국어 키워드 → topic 이름."""
        for topic, words in self._keywords().items():
            if keyword in words:
                return topic
        return None

    def keywordsFor(self, topic: str) -> list[str]:
        """topic → 키워드 목록."""
        return self._keywords().get(topic, [])
