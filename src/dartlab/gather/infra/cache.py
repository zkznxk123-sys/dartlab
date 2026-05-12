"""Gather 엔진 TTL 캐시 — 데이터 유형별 만료 + LRU 축출."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

# TTL 상수 — `infra.ttl` SSOT 에서 import (G+ P-Q4, env override 가능)
from .ttl import (
    TTL_DEFAULT,
    TTL_DIVIDENDS,
    TTL_FLOW,
    TTL_HISTORY,
    TTL_INDEX_MEMBERS,
    TTL_INSIDER,
    TTL_MACRO,
    TTL_MAJOR_HOLDER,
    TTL_MARKET_CAP,
    TTL_NEWS,
    TTL_OWNERSHIP,
    TTL_PRICE,
    TTL_SECTOR,
    TTL_SHORT_SELLING,
    TTL_SNAPSHOT,
    TTL_SPLITS,
)

# 데이터 유형 → TTL 매핑
_TTL_MAP: dict[str, int] = {
    "price": TTL_PRICE,
    "flow": TTL_FLOW,
    "sector_per": TTL_SECTOR,
    "sector_info": TTL_SECTOR,
    "history": TTL_HISTORY,
    "snapshot": TTL_SNAPSHOT,
    "news": TTL_NEWS,
    "dividends": TTL_DIVIDENDS,
    "splits": TTL_SPLITS,
    "macro": TTL_MACRO,
    "short_selling": TTL_SHORT_SELLING,
    "insider": TTL_INSIDER,
    "major_holder": TTL_MAJOR_HOLDER,
    "index_members": TTL_INDEX_MEMBERS,
    "market_cap": TTL_MARKET_CAP,
    "ownership": TTL_OWNERSHIP,
}


@dataclass(slots=True)
class _CacheEntry:
    value: object
    expires_at: float


class GatherCache:
    """TTL 기반 LRU 캐시 — thread-safe + 용량 제한.

    - 데이터 유형별 TTL 자동 적용
    - max_entries 초과 시 가장 오래된 항목 축출
    - 종목별 일괄 무효화 지원
    - stale-while-revalidate: 만료 데이터를 별도 보관하여 최후 fallback 제공
    """

    def __init__(self, maxEntries: int = 200) -> None:
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._stale: dict[str, object] = {}  # 만료 시 마지막 값 보존
        self._max = maxEntries
        self._stale_max = maxEntries  # stale도 용량 제한
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        """캐시 조회 — 만료되었으면 stale로 이동 후 None 반환.

        Parameters
        ----------
        key : str
            캐시 키 (예: "005930:price").

        Returns
        -------
        object | None
            캐시된 값 — 유효한 항목이 있을 때.
            None — 키가 없거나 TTL 만료 시 (만료 데이터는 stale로 이동).

        Raises
        ------
        없음.

        Example
        -------
        >>> v = cache.get("005930:price")
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                # stale store에 보존 후 live에서 제거
                self._stale[key] = entry.value
                del self._store[key]
                self._trimStale()
                return None
            self._store.move_to_end(key)
            return entry.value

    def put(self, key: str, value: object, ttl: int = TTL_DEFAULT) -> None:
        """캐시 저장 — max_entries 초과 시 가장 오래된 항목 LRU 축출.

        Parameters
        ----------
        key : str
            캐시 키 (예: "005930:price").
        value : object
            저장할 데이터.
        ttl : int
            만료 시간 (초). 기본 TTL_DEFAULT (3600초).

        Returns
        -------
        None
            기존 키가 있으면 덮어쓰고, stale 항목도 제거한다.

        Raises
        ------
        없음.

        Example
        -------
        >>> cache.put("005930:price", snap, ttl=300)
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
            self._stale.pop(key, None)  # 새 값 → stale 제거
            self._store[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl,
            )
            while len(self._store) > self._max:
                self._store.popitem(last=False)

    def _trimStale(self) -> None:
        """stale store 용량 제한 — 삽입순으로 가장 오래된 항목부터 제거 (lock 내에서 호출).

        Returns
        -------
        None
            stale_max 초과분만큼 가장 오래된 항목을 삭제한다.
        """
        while len(self._stale) > self._stale_max:
            # dict는 삽입순 — 가장 오래된 것 제거
            first_key = next(iter(self._stale))
            del self._stale[first_key]

    def getStale(self, key: str) -> object | None:
        """만료된 데이터 반환 — stale-while-revalidate 패턴의 최후 fallback.

        Parameters
        ----------
        key : str
            캐시 키 (예: "005930:price").

        Returns
        -------
        object | None
            만료 후 보존된 마지막 값.
            None — stale 항목이 없을 때.

        Raises
        ------
        없음.

        Example
        -------
        >>> stale = cache.getStale("005930:price")
        """
        with self._lock:
            return self._stale.get(key)

    def getTyped(self, stockCode: str, dataType: str, *, allowStale: bool = False) -> object | None:
        """데이터 유형별 캐시 조회 — "{stock_code}:{data_type}" 키로 자동 조합.

        Parameters
        ----------
        stock_code : str
            종목코드 또는 캐시 prefix ("005930", "KR:005930" 등).
        data_type : str
            데이터 유형 ("price", "flow", "snapshot" 등).
        allow_stale : bool
            True이면 live 미스 시 만료 데이터도 반환. 기본 False.

        Returns
        -------
        object | None
            캐시된 값 (PriceSnapshot, ConsensusData, pl.DataFrame 등).
            None — 캐시 미스이고 allow_stale=False이거나 stale도 없을 때.

        Raises
        ------
        없음.

        Example
        -------
        >>> snap = cache.getTyped("005930", "price")
        """
        key = f"{stockCode}:{dataType}"
        result = self.get(key)
        if result is not None:
            return result
        if allowStale:
            return self.getStale(key)
        return None

    def putTyped(self, stockCode: str, dataType: str, value: object) -> None:
        """데이터 유형에 맞는 TTL로 저장 — _TTL_MAP에서 자동 매핑.

        Parameters
        ----------
        stock_code : str
            종목코드 또는 캐시 prefix.
        data_type : str
            데이터 유형 ("price", "flow" 등). _TTL_MAP에 없으면 TTL_DEFAULT (3600초).
        value : object
            저장할 데이터.

        Returns
        -------
        None
            "{stock_code}:{data_type}" 키로 적절한 TTL과 함께 저장한다.

        Raises
        ------
        없음.

        Example
        -------
        >>> cache.putTyped("005930", "price", snap)
        """
        ttl = _TTL_MAP.get(dataType, TTL_DEFAULT)
        self.put(f"{stockCode}:{dataType}", value, ttl)

    def invalidate(self, stockCode: str) -> None:
        """특정 종목의 모든 캐시 제거 — live + stale 양쪽에서 prefix 매칭 삭제.

        Parameters
        ----------
        stock_code : str
            종목코드 ("005930"). "{stock_code}:" prefix로 시작하는 모든 키를 제거.

        Returns
        -------
        None
            해당 종목의 price, flow 등 모든 데이터 유형 캐시를 삭제한다.

        Raises
        ------
        없음.

        Example
        -------
        >>> cache.invalidate("005930")
        """
        with self._lock:
            prefix = f"{stockCode}:"
            for store in (self._store, self._stale):
                keys = [k for k in store if k.startswith(prefix)]
                for k in keys:
                    del store[k]

    def clear(self) -> None:
        """전체 캐시 초기화 — live + stale 모두 비운다.

        Returns
        -------
        None
            모든 캐시 항목을 제거한다. size가 0이 된다.

        Raises
        ------
        없음.

        Example
        -------
        >>> cache.clear()
        """
        with self._lock:
            self._store.clear()
            self._stale.clear()

    @property
    def size(self) -> int:
        """캐시에 저장된 live 항목 수 (stale 제외).

        Returns
        -------
        int
            현재 live 캐시에 저장된 항목 수 (개).

        Raises
        ------
        없음.

        Example
        -------
        >>> cache.size
        """
        return len(self._store)

    def __repr__(self) -> str:
        return f"GatherCache(entries={self.size}, max={self._max})"
