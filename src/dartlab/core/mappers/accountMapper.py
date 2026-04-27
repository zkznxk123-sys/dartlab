"""AccountMapper — accountMappings.json 읽기 전용 래퍼.

기존 labels.py의 _load_account_mappings()가 로드하는 데이터를
MapperEngine 인터페이스로 래핑한다. 원본 코드/데이터 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mappers.engine import BaseMapper, MapperStats


class AccountMapper(BaseMapper):
    """accountMappings.json (34,000+ 매핑) 래퍼."""

    @property
    def name(self) -> str:
        return "account"

    def _data(self) -> dict:
        from dartlab.core.utils.labels import _load_account_mappings

        return _load_account_mappings()

    def _mappings(self) -> dict[str, str]:
        """korName → snakeId 매핑."""
        return self._data().get("mappings", {})

    def _standardAccounts(self) -> dict[str, dict]:
        """{snakeId: {korName, code, level, sj}}."""
        return self._data().get("standardAccounts", {})

    def lookup(self, key: str) -> dict | None:
        """한국어 계정명 또는 snakeId로 조회.

        한국어 → mappings에서 snakeId 찾고 standardAccounts에서 상세 반환.
        snakeId → standardAccounts에서 직접 반환.
        """
        mappings = self._mappings()
        standards = self._standardAccounts()

        # 한국어 계정명 → snakeId
        if key in mappings:
            sid = mappings[key]
            detail = standards.get(sid, {})
            return {"snakeId": sid, **detail}

        # snakeId 직접 조회
        if key in standards:
            return {"snakeId": key, **standards[key]}

        return None

    def stats(self) -> MapperStats:
        data = self._data()
        mappings = data.get("mappings", {})
        standards = data.get("standardAccounts", {})
        meta = data.get("_metadata", {})
        return MapperStats(
            name=self.name,
            totalEntries=len(mappings),
            mappedEntries=len(mappings),
            coverage=1.0 if mappings else 0.0,
            lastUpdated=meta.get("lastUpdate", ""),
        )

    def allKeys(self) -> list[str]:
        return list(self._mappings().keys())

    def snakeIds(self) -> list[str]:
        """등록된 모든 snakeId."""
        return list(self._standardAccounts().keys())

    def korToSnakeId(self, korName: str) -> str | None:
        """한국어 계정명 → snakeId."""
        return self._mappings().get(korName)

    def snakeIdToKor(self, snakeId: str) -> str | None:
        """snakeId → 한국어 계정명."""
        info = self._standardAccounts().get(snakeId)
        return info.get("korName") if info else None
