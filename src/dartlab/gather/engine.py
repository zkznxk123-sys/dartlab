"""Gather 클래스 본체 — 5 mixin 상속 + __init__/invalidate/close/__repr__.

26 메서드는 도메인별 5 mixin (price/info/news/macro/collect) 으로 분리됨
(mixins/ 패키지). 본 모듈은 클래스 시그니처 + 공유 attribute (_client, _cache,
_owns_client) + 4 공통 메서드만 보유.
"""

from __future__ import annotations

from .infra.cache import GatherCache
from .infra.http import GatherHttpClient, runAsync
from .mixins.collect import _GatherCollectMixin
from .mixins.info import _GatherInfoMixin
from .mixins.macro import _GatherMacroMixin
from .mixins.news import _GatherNewsMixin
from .mixins.price import _GatherPriceMixin


class Gather(
    _GatherPriceMixin,
    _GatherInfoMixin,
    _GatherNewsMixin,
    _GatherMacroMixin,
    _GatherCollectMixin,
):
    """통합 멀티소스 비동기 병렬 수집 엔진.

    Capabilities:
        - 개별 조회: price(), flow(), history(), news(), macro() 등 — fallback 체인
        - 전체 수집: collect() — 도메인별 asyncio.gather 병렬
        - 캐시: TTL 기반 데이터 유형별 자동 만료 (GatherCache)
        - circuit breaker: 실패 도메인 자동 격리/복구
        - 시장 지원: KR (Naver/ECOS), US (Yahoo/FRED/FMP)

    Guide:
        - AI 역할: AI는 Gather를 외부 데이터 수집 실행 엔진으로 보고 축별 수집 가능성, 시장, 캐시/네트워크 한계를 먼저 확인한다.
        - "주가 보여줘" -> g.price("005930")
        - "현재가 알려줘" -> g.price("005930", snapshot=True)
        - "외국인 매매 동향" -> g.flow("005930")
        - "거시지표 전체" -> g.macro() 또는 g.macro("US")
        - "금리 추이" -> g.macro("FEDFUNDS") (자동 US 감지)
        - "뉴스 검색" -> g.news("삼성전자")
        - "전부 한번에" -> g.collect("005930") (병렬 수집 스냅샷)
        - 공개 API 진입점은 dartlab.gather(). 내부 엔진은 이 클래스.

    SeeAlso:
        - GatherEntry: dartlab.gather() 공개 API (3단계 패턴)
        - scan: 재무 기반 전종목 횡단분석
        - Company: 개별 종목 공시/재무 데이터

    Args:
        client: GatherHttpClient 인스턴스. None이면 내부 생성.

    Returns:
        Gather 인스턴스.

    Requires:
        없음 (API 키는 macro() 호출 시 필요).

    Example::

        from dartlab.gather import Gather, getDefaultGather

        g = getDefaultGather()           # 싱글턴 (권장)
        g.price("005930")               # 삼성전자 1년 OHLCV
        g.flow("005930")                # 수급 시계열
        g.macro()                       # KR 거시지표 전체
        snap = g.collect("005930")      # 전체 병렬 수집
    """

    def __init__(self, client: GatherHttpClient | None = None) -> None:
        self._client = client or GatherHttpClient()
        self._cache = GatherCache()
        self._owns_client = client is None

    def invalidate(self, stockCode: str) -> None:
        """특정 종목의 캐시 무효화 — live + stale 모두 제거.

        Capabilities: GatherCache.invalidate(stockCode) 위임 — TTL 모든 axis 제거.
        AIContext: 사용자가 신선 데이터 강제 시 / 외부 API 변경 후 캐시 회수 시 진입.
        Guide: 종목 한정 — 전체 캐시 비우려면 close() + 새 인스턴스.
        When: live 가격 / flow 갱신 후 재호출 필요 시.
        How: ``self._cache.invalidate(stockCode)`` direct forward.

        Parameters
        ----------
        stock_code : str
            캐시를 삭제할 종목코드 ("005930").

        Returns
        -------
        None
            캐시에서 해당 종목의 모든 데이터 유형 항목을 제거한다.

        Raises
        ------
        없음
            미존재 종목은 silent (cache.invalidate 가 graceful).

        Requires
        --------
        Gather instance + ``_cache`` 가용.

        Example::

            g = getDefaultGather()
            g.invalidate("005930")   # 삼성전자 캐시 제거

        See Also
        --------
        close : 모든 리소스 정리.
        infra.cache.GatherCache.invalidate : 위임 대상.
        """
        self._cache.invalidate(stockCode)

    def close(self) -> None:
        """HTTP 클라이언트 등 리소스 정리 — 자체 생성한 클라이언트만 닫는다.

        Capabilities: ``_owns_client`` 분기 → 자체 생성 client 일 경우만 ``aclose`` 호출.
        AIContext: 외부 주입 client (테스트/CLI) 는 caller 가 close 책임 — 본 함수는 owner 일 때만.
        Guide: idempotent — 두 번 호출해도 graceful.
        When: dartlab 종료 / context manager exit / 명시 cleanup 시.
        How: ``if self._owns_client: runAsync(self._client.aclose())``.

        Returns
        -------
        None
            _owns_client=True일 때만 내부 GatherHttpClient 세션을 종료한다.

        Raises
        ------
        없음
            클라이언트 close 는 graceful.

        Requires
        --------
        ``_client`` (GatherHttpClient) + ``_owns_client`` 필드.

        Example
        -------
        >>> g = Gather()
        >>> g.close()

        See Also
        --------
        invalidate : 종목 단위 캐시만 제거 (resource 유지).
        infra.http.GatherHttpClient.aclose : 위임 대상.
        """
        if self._owns_client:
            runAsync(self._client.close())

    def __repr__(self) -> str:
        return f"Gather(cache={self._cache})"


__all__ = ["Gather"]
