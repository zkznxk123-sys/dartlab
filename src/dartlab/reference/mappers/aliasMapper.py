"""AliasMapper — SNAKEID_ALIASES 읽기 전용 래퍼.

기존 labels.py의 SNAKEID_ALIASES(61 alias)를
MapperEngine 인터페이스로 래핑한다. 원본 코드 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mapperEngine import BaseMapper, MapperStats


class AliasMapper(BaseMapper):
    """SNAKEID_ALIASES (variant → canonical snakeId) 래퍼."""

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
            >>> AliasMapper().name
            'alias'
        """
        return "alias"

    def _aliases(self) -> dict[str, str]:
        from dartlab.core.utils.labels import SNAKEID_ALIASES

        return SNAKEID_ALIASES

    def lookup(self, key: str) -> dict | None:
        """variant snakeId → canonical 매핑 조회.

        canonical 자체를 넣으면 역방향(어떤 variant들이 이 canonical을 가리키는지).

        Capabilities:
            Resolves alias variants and reverse-lists variants for a canonical id.
        AIContext:
            Keeps financial account synonyms aligned before analysis or scan lookup.
        Guide:
            Use ``resolve`` when only the canonical string is needed.
        When:
            Called by mapper engine consumers resolving snakeId variants.
        How:
            Checks variant-to-canonical mapping first, then reverse searches canonical values.
        Args:
            key: Variant or canonical snakeId.
        Returns:
            Mapping detail dict or ``None``.
        Requires:
            ``SNAKEID_ALIASES`` from core labels.
        Raises:
            Propagates labels import errors.
        Example:
            >>> AliasMapper().lookup("__missing__") is None
            True
        SeeAlso:
            ``resolve`` and ``variantsOf``.
        """
        aliases = self._aliases()

        # variant → canonical
        if key in aliases:
            return {"variant": key, "canonical": aliases[key]}

        # canonical 역방향 — 이 canonical을 가리키는 variant 목록
        variants = [v for v, c in aliases.items() if c == key]
        if variants:
            return {"canonical": key, "variants": variants}

        return None

    def stats(self) -> MapperStats:
        """Return alias mapper statistics.

        Capabilities:
            Reports alias entry counts.
        AIContext:
            Helps audits inspect synonym coverage.
        Guide:
            Use for diagnostics, not hot-path canonicalization.
        When:
            Called by mapper engine summaries.
        How:
            Counts variant and canonical ids from ``SNAKEID_ALIASES``.
        Args:
            None.
        Returns:
            ``MapperStats`` for alias mappings.
        Requires:
            ``SNAKEID_ALIASES`` from core labels.
        Raises:
            Propagates labels import errors.
        Example:
            >>> AliasMapper().stats().name
            'alias'
        SeeAlso:
            ``MapperStats``.
        """
        aliases = self._aliases()
        canonicals = set(aliases.values())
        return MapperStats(
            name=self.name,
            totalEntries=len(aliases),
            mappedEntries=len(aliases),
            coverage=1.0,
            lastUpdated="",
        )

    def allKeys(self) -> list[str]:
        """Return all alias variant keys.

        Args:
            None.

        Returns:
            Alias variant key list.

        Requires:
            ``SNAKEID_ALIASES`` from core labels.

        Raises:
            Propagates labels import errors.

        Example:
            >>> isinstance(AliasMapper().allKeys(), list)
            True
        """
        return list(self._aliases().keys())

    def resolve(self, snakeId: str) -> str:
        """snakeId를 canonical로 정규화. 매핑 없으면 원본 반환.

        Args:
            snakeId: Candidate snakeId.

        Returns:
            Canonical snakeId, or original value when no alias exists.

        Requires:
            ``SNAKEID_ALIASES`` from core labels.

        Raises:
            Propagates labels import errors.

        Example:
            >>> AliasMapper().resolve("__missing__")
            '__missing__'
        """
        return self._aliases().get(snakeId, snakeId)

    def canonicals(self) -> list[str]:
        """모든 canonical snakeId.

        Args:
            None.

        Returns:
            Sorted canonical snakeId list.

        Requires:
            ``SNAKEID_ALIASES`` from core labels.

        Raises:
            Propagates labels import errors.

        Example:
            >>> isinstance(AliasMapper().canonicals(), list)
            True
        """
        return sorted(set(self._aliases().values()))

    def variantsOf(self, canonical: str) -> list[str]:
        """특정 canonical을 가리키는 모든 variant.

        Args:
            canonical: Canonical snakeId.

        Returns:
            Variant snakeIds pointing at ``canonical``.

        Requires:
            ``SNAKEID_ALIASES`` from core labels.

        Raises:
            Propagates labels import errors.

        Example:
            >>> AliasMapper().variantsOf("__missing__")
            []
        """
        return [v for v, c in self._aliases().items() if c == canonical]
