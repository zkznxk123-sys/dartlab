"""AliasMapper — SNAKEID_ALIASES 읽기 전용 래퍼.

기존 labels.py의 SNAKEID_ALIASES(61 alias)를
MapperEngine 인터페이스로 래핑한다. 원본 코드 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mappers.engine import BaseMapper, MapperStats


class AliasMapper(BaseMapper):
    """SNAKEID_ALIASES (variant → canonical snakeId) 래퍼."""

    @property
    def name(self) -> str:
        return "alias"

    def _aliases(self) -> dict[str, str]:
        from dartlab.core.utils.labels import SNAKEID_ALIASES

        return SNAKEID_ALIASES

    def lookup(self, key: str) -> dict | None:
        """variant snakeId → canonical 매핑 조회.

        canonical 자체를 넣으면 역방향(어떤 variant들이 이 canonical을 가리키는지).
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
        return list(self._aliases().keys())

    def resolve(self, snakeId: str) -> str:
        """snakeId를 canonical로 정규화. 매핑 없으면 원본 반환."""
        return self._aliases().get(snakeId, snakeId)

    def canonicals(self) -> list[str]:
        """모든 canonical snakeId."""
        return sorted(set(self._aliases().values()))

    def variantsOf(self, canonical: str) -> list[str]:
        """특정 canonical을 가리키는 모든 variant."""
        return [v for v, c in self._aliases().items() if c == canonical]
