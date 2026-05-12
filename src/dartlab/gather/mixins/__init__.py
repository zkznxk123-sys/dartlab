"""Gather 클래스 도메인 mixin — 26 메서드를 5 카테고리로 분리.

`engine.Gather` 가 본 패키지의 5 mixin 을 상속한다. mixin 끼리는 서로 의존하지
않고 `self._client`, `self._cache`, `self._owns_client` 만 공유. mixin 호출
패턴은 외부 caller 시점에 동일 (`g.price()`, `g.flow()`, ...).

facade re-export 하지 않는다 — mixin 은 engine.py 가 직접 import.
"""
