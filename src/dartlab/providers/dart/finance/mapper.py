"""항목 → snakeId 매핑 하위 호환 facade — 본체는 ``dartlab.core.accounts``.

12 단계 fallback·in-code 동의어 dict 가 ``core/accounts/`` 단일 소유 SSOT 엔진으로
통합됐다. 본 모듈은 기존 import 경로를 보존하는 *얇은 위임 facade*:

- ``AccountMapper`` — ``core.accounts.AccountNormalizer.normalize`` 위임 + 라벨/순서 헬퍼
- ``ID_SYNONYMS`` / ``ACCOUNT_NAME_SYNONYMS`` — SSOT ``layers`` 직접 노출
- ``_PREFIX_RE`` / ``_PAREN_RE`` / ``_KOR_TRIM_SUFFIXES`` / ``_stripPrefix`` — 정규화 상수

새 코드는 ``dartlab.core.accounts`` 를 직접 import 한다.
"""

from __future__ import annotations

from typing import Optional

from dartlab.core.accounts import release as _release
from dartlab.core.accounts.data import loadAccounts
from dartlab.core.accounts.normalize import (
    _KOR_TRIM_SUFFIXES,
    _PAREN_RE,
    _PREFIX_RE,
    AccountNormalizer,
)
from dartlab.core.accounts.normalize import (
    stripPrefix as _stripPrefix,
)
from dartlab.core.utils.ordering import levelMap as _commonLevelMap
from dartlab.core.utils.ordering import sortOrder as _commonSortOrder

# 옛 in-code 동의어 dict — SSOT layers 직접 노출 (동일 객체 identity 보존)
ID_SYNONYMS: dict[str, str] = loadAccounts()["layers"]["idSynonym"]
ACCOUNT_NAME_SYNONYMS: dict[str, str] = loadAccounts()["layers"]["nameSynonym"]

__all__ = [
    "AccountMapper",
    "ID_SYNONYMS",
    "ACCOUNT_NAME_SYNONYMS",
    "_PREFIX_RE",
    "_PAREN_RE",
    "_KOR_TRIM_SUFFIXES",
    "_stripPrefix",
]


class AccountMapper:
    """항목 매핑기 facade — ``core.accounts.AccountNormalizer`` 위임.

    ``map()`` 은 12 단계 fallback 본체에 위임하고, ``labelMap``/``sortOrder``/
    ``levelMap`` 은 라벨 cascade·순서 SSOT 에 위임한다.
    """

    _instance: Optional[AccountMapper] = None

    @classmethod
    def get(cls) -> AccountMapper:
        """싱글턴 facade 인스턴스.

        Args:
            없음.

        Returns:
            동일 process 안 항상 같은 ``AccountMapper``.

        Raises:
            없음.

        Example:
            >>> AccountMapper.get().map("ifrs-full_Revenue", "매출액")
            'sales'
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def release(cls) -> None:
        """facade + 본체 전 캐시 무효화 — SSOT 편집 후.

        Args:
            없음.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> AccountMapper.release()
        """
        cls._instance = None
        _release()

    def map(self, accountId: str, accountNm: str) -> Optional[str]:
        """``account_id`` + ``account_nm`` → snakeId (12 단계 fallback 위임).

        Args:
            accountId: XBRL account_id (prefix 포함 raw).
            accountNm: 한글 account_nm.

        Returns:
            snakeId 또는 None (미매핑).

        Raises:
            없음.

        Example:
            >>> AccountMapper.get().map("ifrs-full_Revenue", "매출액")
            'sales'
        """
        return AccountNormalizer.get().normalize(accountId, accountNm)

    def labelMap(self) -> dict[str, str]:
        """``snakeId`` → 대표 한글명 (라벨 cascade SSOT 위임).

        Args:
            없음.

        Returns:
            ``{snakeId: 한글 라벨}`` dict.

        Raises:
            없음.

        Example:
            >>> AccountMapper.get().labelMap()["sales"]
            '매출액'
        """
        from dartlab.core.accounts import koreanLabels

        return koreanLabels()

    def sortOrder(self, sjDiv: str) -> dict[str, int]:
        """``sj_div`` 별 snakeId → 표시 순서 (ordering SSOT 위임).

        Args:
            sjDiv: BS/IS/CF/CIS/SCE.

        Returns:
            ``{snakeId: 순서}`` dict.

        Raises:
            없음.

        Example:
            >>> AccountMapper.get().sortOrder("IS")["sales"]
            10
        """
        return _commonSortOrder(sjDiv)

    def levelMap(self, sjDiv: str) -> dict[str, int]:
        """``sj_div`` 별 snakeId → 들여쓰기 레벨 (ordering SSOT 위임).

        Args:
            sjDiv: BS/IS/CF/CIS/SCE.

        Returns:
            ``{snakeId: 레벨}`` dict.

        Raises:
            없음.

        Example:
            >>> AccountMapper.get().levelMap("BS")["current_assets"]
            1
        """
        return _commonLevelMap(sjDiv)
