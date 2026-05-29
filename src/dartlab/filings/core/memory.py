"""메모리 가드 — BoundedCache (LRU) + Company context-manager 정리.

Polars 네이티브 힙은 gc 회수 불가 → multi-company 루프 시 cache 무한 누적이 OOM
유발. BoundedCache 가 in-memory 프레임 수를 cap, Company.__exit__ 가 cache 비움.

LLM Specifications:
    AntiPatterns:
        - 무한 dict cache 금지 — maxsize 강제 LRU eviction.
        - per-company 프레임을 모듈 전역에 캐시 금지 — Company 인스턴스 scope.
    OutputSchema:
        - ``BoundedCache(maxsize)`` — get/set/contains/clear.
    Prerequisites:
        - 없음 (stdlib).
    TargetMarkets:
        - 공통.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


class BoundedCache:
    """LRU 캐시 — maxsize 초과 시 가장 오래된 항목 evict.

    Examples:
        >>> c = BoundedCache(maxsize=2)
        >>> c["a"] = 1; c["b"] = 2; c["c"] = 3   # "a" evict
        >>> "a" in c, "c" in c
        (False, True)
    """

    def __init__(self, maxsize: int = 32):
        self._d: "OrderedDict[str, Any]" = OrderedDict()
        self._max = max(1, maxsize)

    def __contains__(self, key: str) -> bool:
        return key in self._d

    def __getitem__(self, key: str) -> Any:
        self._d.move_to_end(key)
        return self._d[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._d[key] = value
        self._d.move_to_end(key)
        while len(self._d) > self._max:
            self._d.popitem(last=False)

    def get(self, key: str, default: Any = None) -> Any:
        """키 조회 (LRU 갱신). 없으면 default 반환."""
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return default

    def clear(self) -> None:
        """전체 캐시 비움 — Company.__exit__ 에서 호출 (멀티 회사 루프 RSS 회수)."""
        self._d.clear()

    def __len__(self) -> int:
        return len(self._d)
