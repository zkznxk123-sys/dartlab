"""TopicMapper — TOPIC_KEYWORDS 읽기 전용 래퍼.

기존 topicGraph.py의 TOPIC_KEYWORDS(33 topics)를
MapperEngine 인터페이스로 래핑한다. 원본 코드 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mapperEngine import BaseMapper, MapperStats


class TopicMapper(BaseMapper):
    """TOPIC_KEYWORDS (33 topics → 한국어 키워드) 래퍼."""

    @property
    def name(self) -> str:
        """Return mapper registry name.

        Args:
            None.

        Returns:
            Registry key for this mapper.

        Requires:
            None.

        Raises:
            None.

        Example:
            >>> TopicMapper().name
            'topic'
        """
        return "topic"

    def _keywords(self) -> dict[str, list[str]]:
        from dartlab.reference.docs.topicGraph import TOPIC_KEYWORDS

        return TOPIC_KEYWORDS

    def lookup(self, key: str) -> dict | None:
        """topic 이름으로 키워드 목록 조회.

        영문 topic key 또는 한국어 키워드 역방향 조회.

        Capabilities:
            Looks up topic keyword sets and reverse-maps Korean keywords to topics.
        AIContext:
            Gives disclosure and narrative flows a stable topic vocabulary.
        Guide:
            Use ``topicForKeyword`` when only reverse topic id is needed.
        When:
            Called while matching user topics or disclosure section labels.
        How:
            Checks direct topic key first, then scans keyword lists for a Korean match.
        Args:
            key: Topic id or Korean keyword.
        Returns:
            Topic detail dict or ``None``.
        Requires:
            ``TOPIC_KEYWORDS`` from reference topic graph.
        Raises:
            Propagates topic graph import errors.
        Example:
            >>> TopicMapper().lookup("__missing__") is None
            True
        SeeAlso:
            ``topicForKeyword`` and ``keywordsFor``.
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
        """Return topic mapper statistics.

        Capabilities:
            Reports topic and keyword counts.
        AIContext:
            Helps audits inspect disclosure topic coverage.
        Guide:
            Use for diagnostics, not per-token matching.
        When:
            Called by mapper summaries and tests.
        How:
            Counts topic keys and nested keyword values.
        Args:
            None.
        Returns:
            ``MapperStats`` for topic mappings.
        Requires:
            ``TOPIC_KEYWORDS`` from reference topic graph.
        Raises:
            Propagates topic graph import errors.
        Example:
            >>> TopicMapper().stats().name
            'topic'
        SeeAlso:
            ``MapperStats``.
        """
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
        """Return all topic keys.

        Args:
            None.

        Returns:
            Topic key list.

        Requires:
            ``TOPIC_KEYWORDS`` from reference topic graph.

        Raises:
            Propagates topic graph import errors.

        Example:
            >>> isinstance(TopicMapper().allKeys(), list)
            True
        """
        return list(self._keywords().keys())

    def topicForKeyword(self, keyword: str) -> str | None:
        """한국어 키워드 → topic 이름.

        Args:
            keyword: Korean keyword.

        Returns:
            Topic id or ``None``.

        Requires:
            ``TOPIC_KEYWORDS`` from reference topic graph.

        Raises:
            Propagates topic graph import errors.

        Example:
            >>> TopicMapper().topicForKeyword("__missing__") is None
            True
        """
        for topic, words in self._keywords().items():
            if keyword in words:
                return topic
        return None

    def keywordsFor(self, topic: str) -> list[str]:
        """topic → 키워드 목록.

        Args:
            topic: Topic id.

        Returns:
            Keyword list, or an empty list for unknown topics.

        Requires:
            ``TOPIC_KEYWORDS`` from reference topic graph.

        Raises:
            Propagates topic graph import errors.

        Example:
            >>> TopicMapper().keywordsFor("__missing__")
            []
        """
        return self._keywords().get(topic, [])
