"""ListingResolver 구현 + register (정공법 B — DIP).

core/providers 가 gather/listing.py 직접 import 안 함. 모듈 load 시점에
``_registerGatherListingResolver()`` 자동 호출 → core/listingResolver.py
의 registerListingResolver(GatherListingResolver()).
"""

from __future__ import annotations

import polars as pl

from .registry import codeToName, getKindList, nameToCode


class GatherListingResolver:
    """ListingResolver 구현 — core/resolve.py + providers/dart/Company 가 이 인스턴스 사용 (registry 경유).

    core/providers 가 gather/listing.py 직접 import 안 함. module load 시점에 register.
    """

    def search(self, query: str, *, limit: int | None = None) -> pl.DataFrame | None:
        """회사명 검색 — searchName 위임.

        Parameters
        ----------
        query : str
            검색어.
        limit : int | None
            반환 행수 상한 (가장 관련도 높은 N). None이면 전체.

        Returns
        -------
        pl.DataFrame | None
            매칭된 종목 DataFrame. 위임 실패 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.search("삼성", limit=10)
        """
        try:
            from .fuzzy import searchName

            return searchName(query, limit=limit)
        except (ValueError, OSError):
            return None

    def fuzzy(self, query: str, *, maxResults: int = 5) -> pl.DataFrame | None:
        """fuzzy 검색 — fuzzySearch 위임.

        Parameters
        ----------
        query : str
            검색어 (한글/영문/초성).
        maxResults : int
            최대 결과 수. 기본 5.

        Returns
        -------
        pl.DataFrame | None
            관련도 순 매칭 DataFrame. 위임 실패 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.fuzzy("삼전", maxResults=5)
        """
        try:
            from .fuzzy import fuzzySearch

            return fuzzySearch(query, maxResults=maxResults)
        except (ValueError, OSError):
            return None

    def codeToName(self, stockCode: str) -> str | None:
        """stockCode → 회사명 변환.

        Parameters
        ----------
        stockCode : str
            6자리 종목코드.

        Returns
        -------
        str | None
            회사명. 위임 실패 또는 미존재 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> r.codeToName("005930")
        """
        try:
            return codeToName(stockCode)
        except (ValueError, OSError):
            return None

    def nameToCode(self, corpName: str) -> str | None:
        """회사명 → stockCode 변환.

        Parameters
        ----------
        corpName : str
            회사명 (정확한 매칭).

        Returns
        -------
        str | None
            6자리 종목코드. 위임 실패 또는 미존재 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> r.nameToCode("삼성전자")
        """
        try:
            return nameToCode(corpName)
        except (ValueError, OSError):
            return None

    def kindList(self, *, forceRefresh: bool = False) -> pl.DataFrame:
        """KIND 상장법인 목록.

        Parameters
        ----------
        forceRefresh : bool
            True면 캐시 무시 재요청.

        Returns
        -------
        pl.DataFrame
            전체 상장법인 목록 — getKindList 와 동일 스키마.

        Raises
        ------
        없음
            getKindList 가 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.kindList()
        """
        return getKindList(forceRefresh=forceRefresh)


def _registerGatherListingResolver() -> None:
    """import 시점 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.listingResolver import registerListingResolver

    registerListingResolver(GatherListingResolver())


_registerGatherListingResolver()
