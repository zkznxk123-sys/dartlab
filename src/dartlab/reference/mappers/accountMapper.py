"""AccountMapper — accountMappings.json 읽기 전용 래퍼.

기존 labels.py의 _load_account_mappings()가 로드하는 데이터를
MapperEngine 인터페이스로 래핑한다. 원본 코드/데이터 수정 0줄.
"""

from __future__ import annotations

from dartlab.core.mapperEngine import BaseMapper, MapperStats


class AccountMapper(BaseMapper):
    """accountMappings.json (34,000+ 매핑) 래퍼."""

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
            >>> AccountMapper().name
            'account'
        """
        return "account"

    def _data(self) -> dict:
        from dartlab.core.utils.labels import _loadAccountMappings

        return _loadAccountMappings()

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

        Capabilities:
            Account mapping lookup by Korean label or canonical snakeId.
        AIContext:
            Used when natural-language finance labels must resolve to stable account ids.
        Guide:
            Prefer this over reading ``accountMappings.json`` directly.
        When:
            Called by mapper engine consumers during account normalization.
        How:
            Checks Korean mapping first, then direct standard account id lookup.
        Args:
            key: Korean account name or snakeId.
        Returns:
            Account detail dict or ``None``.
        Requires:
            Bundled account mapping data.
        Raises:
            Propagates mapping data load errors.
        Example:
            >>> AccountMapper().lookup("__missing__") is None
            True
        SeeAlso:
            ``korToSnakeId`` and ``snakeIdToKor``.
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
        """Return account mapper statistics.

        Capabilities:
            Reports mapping entry counts and metadata freshness.
        AIContext:
            Helps audits summarize mapper coverage.
        Guide:
            Use for diagnostics, not per-row mapping.
        When:
            Called by ``MapperEngine.summary`` and audit tests.
        How:
            Counts mapping and standard account entries from the bundled data.
        Args:
            None.
        Returns:
            ``MapperStats`` for account mappings.
        Requires:
            Bundled account mapping data.
        Raises:
            Propagates mapping data load errors.
        Example:
            >>> AccountMapper().stats().name
            'account'
        SeeAlso:
            ``MapperStats``.
        """
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
        """Return all Korean account names.

        Args:
            None.

        Returns:
            Korean account name list.

        Requires:
            Bundled account mapping data.

        Raises:
            Propagates mapping data load errors.

        Example:
            >>> isinstance(AccountMapper().allKeys(), list)
            True
        """
        return list(self._mappings().keys())

    def snakeIds(self) -> list[str]:
        """등록된 모든 snakeId.

        Args:
            None.

        Returns:
            Registered snakeId list.

        Requires:
            Bundled standard account data.

        Raises:
            Propagates mapping data load errors.

        Example:
            >>> isinstance(AccountMapper().snakeIds(), list)
            True
        """
        return list(self._standardAccounts().keys())

    def korToSnakeId(self, korName: str) -> str | None:
        """한국어 계정명 → snakeId.

        Args:
            korName: Korean account name.

        Returns:
            snakeId or ``None``.

        Requires:
            Bundled account mapping data.

        Raises:
            Propagates mapping data load errors.

        Example:
            >>> AccountMapper().korToSnakeId("__missing__") is None
            True
        """
        return self._mappings().get(korName)

    def snakeIdToKor(self, snakeId: str) -> str | None:
        """snakeId → 한국어 계정명.

        Args:
            snakeId: Canonical account snakeId.

        Returns:
            Korean account name or ``None``.

        Requires:
            Bundled standard account data.

        Raises:
            Propagates mapping data load errors.

        Example:
            >>> AccountMapper().snakeIdToKor("__missing__") is None
            True
        """
        info = self._standardAccounts().get(snakeId)
        return info.get("korName") if info else None
