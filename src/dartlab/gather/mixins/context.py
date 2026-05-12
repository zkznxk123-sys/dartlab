"""Gather mixin attribute 계약 — Protocol 명시 (G+ P-Q3).

5 mixin (price/info/news/macro/collect) 본문은 ``self._client`` /
``self._cache`` / ``self._owns_client`` 3 attribute 를 가정한다. 본 Protocol
정식화로 mypy/pyright 가 mixin 단독 분석 시에도 attribute 존재를 인식한다.

Engine 본체 (``engine.Gather``) 가 이 3 attribute 를 ``__init__`` 에서 주입.
mixin 클래스는 ``class _GatherPriceMixin(GatherMixinContext):`` 패턴으로
Protocol 을 상속 — Protocol 이므로 runtime 동작 변경 0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..infra.cache import GatherCache
    from ..infra.http import GatherHttpClient


class GatherMixinContext(Protocol):
    """5 mixin 이 self 로 가정하는 attribute 계약 — Engine 본체가 주입.

    Capabilities:
        - mixin 단독 분석 시 self._client / self._cache / self._owns_client
          attribute 존재를 typing 도구에 알린다.

    AIContext:
        - mixin 작성/리뷰 시 attribute 의존을 명시 — Engine 책임 경계 인식.

    Guide:
        Engine 본체는 ``__init__`` 에서 _client / _cache 인스턴스를 생성
        또는 외부 주입 받는다. _owns_client 가 True 면 ``close()`` 가
        _client 도 닫는다.

    When:
        새 mixin 추가 시. 또는 mixin 본문 typing 정합성 검증 시.

    How:
        mixin 클래스 정의:
            ``class _GatherFooMixin(GatherMixinContext): ...``
        Engine 본체:
            ``class Gather(_GatherPriceMixin, _GatherInfoMixin, ...): ...``

    Requires:
        Engine 본체가 _client (GatherHttpClient) / _cache (GatherCache)
        / _owns_client (bool) 3 attribute 를 __init__ 직후 보유.

    Raises:
        없음 — Protocol 은 runtime 검증 안 함 (typing 전용).

    Example::

        class _GatherPriceMixin(GatherMixinContext):
            def price(self, stockCode: str) -> "pl.DataFrame":
                cached = self._cache.getTyped(...)  # mypy OK
                return self._client.fetch(...)      # mypy OK

    See Also:
        ``engine.Gather`` — 본 Protocol 의 concrete 구현.
        ``infra.http.GatherHttpClient`` — _client 의 타입.
        ``infra.cache.GatherCache`` — _cache 의 타입.
    """

    _client: GatherHttpClient
    _cache: GatherCache
    _owns_client: bool
