"""GatherProvider Protocol 구현체 + Gather 싱글턴 진입점.

dartlab.core.gatherProvider.GatherProvider Protocol 의 dartlab.gather 측
구현 — providers 가 gather 본체를 직접 참조하지 않고 Protocol 경유로
news/entry 위임 호출. 모듈 import 시 자동 등록 (side-effect).
"""

from __future__ import annotations

import threading
from typing import Any

from .main import GatherEntry


class _GatherProviderAdapter:
    """GatherProvider Protocol 구현체 — gather/entry · getDefaultGather 위임체."""

    def news(self, query: str, *, market: str = "KR", days: int = 30) -> Any | None:
        """뉴스 수집 — gather.getDefaultGather().news 위임.

        Args:
            query: 검색어 (기업명/티커).
            market: 시장 코드 (``"KR"`` | ``"US"``).
            days: 최근 N일.

        Returns:
            ``(date, title, source, url)`` DataFrame. fetch 실패 시 None.

        Raises:
            없음 — 위임 함수의 예외는 호출자가 처리.

        Example:
            >>> a = _GatherProviderAdapter()
            >>> df = a.news("삼성전자", market="KR", days=7)
        """
        return getDefaultGather().news(query, market=market, days=days)

    def entry(self, axis: str | None = None, stockCode: str | None = None, **kwargs: Any) -> Any:
        """4축 entry 위임 — GatherEntry() callable 호출.

        Args:
            axis: 축 이름 ("price"/"flow"/"macro"/"news" 등). None이면 가이드.
            stockCode: 종목코드/티커.
            **kwargs: market, start, end, days 등 축별 옵션.

        Returns:
            축별 시계열 DataFrame. axis=None이면 가이드 DataFrame.

        Raises:
            ValueError: 미등록 축 이름 또는 target 누락.

        Example:
            >>> a = _GatherProviderAdapter()
            >>> df = a.entry("price", "005930")
        """
        gather = GatherEntry()
        if axis is None:
            return gather()
        if stockCode is None:
            return gather(axis, **kwargs)
        return gather(axis, stockCode, **kwargs)


# ── Gather 싱글턴 진입점 (룰 4 thin: gather/__init__.py 의 함수 정의를 모듈로 이동) ──

_defaultGather: object | None = None
_defaultGatherLock: threading.Lock = threading.Lock()


def getDefaultGather():
    """Gather 싱글턴 반환 — 같은 세션 내 캐시/HTTP 클라이언트 재사용.

    Thread-safe — double-checked locking 으로 멀티스레드 환경에서도 단일 인스턴스
    보장. lock 미보유 fast-path 가 정상 케이스 (이미 초기화) latency 무시 가능.

    Returns:
        Gather — 싱글턴 인스턴스 (첫 호출 시 자동 생성).

    Raises:
        없음 — Gather() 생성자가 lazy 초기화를 보장.

    Example::

        from dartlab.gather import getDefaultGather
        g = getDefaultGather()
        g.price("005930")
    """
    global _defaultGather
    if _defaultGather is None:
        with _defaultGatherLock:
            if _defaultGather is None:
                from dartlab.gather.engine import Gather

                _defaultGather = Gather()
    return _defaultGather


# ── 모듈 import 시 자동 등록 (side-effect) ──

from dartlab.core.gatherProvider import registerGatherProvider as _registerGatherProvider

_registerGatherProvider(_GatherProviderAdapter())
