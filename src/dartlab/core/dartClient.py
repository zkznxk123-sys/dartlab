"""DART OpenAPI fetch seam — DI Protocol (정공법 B).

gather 가 모든 DART network fetch 를 전담(ETL Extract). providers 의 build/read
코드가 client·키가 필요하면 본 core seam 으로 접근 — providers↛gather 단방향 유지.
``gather/dart/client.py`` 의 ``DartFetchProvider`` 구현이 import 시점에 register.

``DartApiError`` 는 pure infra 예외라 core 에 정의(공유 식별자) — gather 가 raise,
providers 가 except 한다. 본 모듈의 ``DartClient`` 는 *factory 함수* — 소비자
호출부(``DartClient(...)``)는 그대로 두고 import 경로만 본 모듈로 교체하면 된다.

CredentialProvider/LoaderProvider/DisclosureFetcher 와 동일 패턴.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class DartApiError(Exception):
    """OpenDART API 에러 (공유 infra 예외 — gather raise, providers except)."""

    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")


@runtime_checkable
class DartFetchProvider(Protocol):
    """DART fetch 추상화 — providers build/read 가 client·키를 얻는 seam."""

    def makeClient(
        self,
        apiKey: str | None = None,
        apiKeys: list[str] | None = None,
        requestsPerMinute: int = 580,
    ) -> Any:
        """멀티 키 DART HTTP 클라이언트 인스턴스 생성."""
        ...

    def resolveKeys(self, apiKey: str | None = None, apiKeys: list[str] | None = None) -> list[str]:
        """DART API 키 list resolve (env/.env/파라미터)."""
        ...

    def hasKey(self) -> bool:
        """DART API 키 설정 여부."""
        ...


_PROVIDER: DartFetchProvider | None = None

_KNOWN_PROVIDER_MODULES: tuple[str, ...] = ("dartlab.gather.dart.client",)
_DISCOVERED = False


def _discover() -> None:
    """알려진 DartFetchProvider 모듈을 한 번만 lazy import — register 트리거."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_PROVIDER_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue
    _DISCOVERED = True


def registerDartFetchProvider(provider: DartFetchProvider) -> None:
    """DartFetchProvider 등록 — gather/dart/client 가 import 시점에 호출."""
    global _PROVIDER
    _PROVIDER = provider


def getDartFetchProvider() -> DartFetchProvider | None:
    """현재 등록된 DartFetchProvider 반환. 미등록이면 None. auto-discovery 트리거."""
    _discover()
    return _PROVIDER


def _provider() -> DartFetchProvider:
    provider = getDartFetchProvider()
    if provider is None:
        raise RuntimeError("DartFetchProvider 미등록 — dartlab.gather.dart.client import 실패 (gather 미설치/오류)")
    return provider


def DartClient(
    apiKey: str | None = None,
    apiKeys: list[str] | None = None,
    requestsPerMinute: int = 580,
) -> Any:
    """DART OpenAPI 클라이언트 factory — gather DartFetchProvider 위임.

    Requires: ``dartlab.gather.dart.client`` (DartFetchProvider 등록) + DART_API_KEY(S).
    Raises: RuntimeError — DartFetchProvider 미등록. ValueError — 키 부재.
    Example:
        >>> from dartlab.core.dartClient import DartClient  # doctest: +SKIP
        >>> client = DartClient()  # gather DartClient 인스턴스
    """
    return _provider().makeClient(apiKey=apiKey, apiKeys=apiKeys, requestsPerMinute=requestsPerMinute)


def resolveDartKeys(apiKey: str | None = None, apiKeys: list[str] | None = None) -> list[str]:
    """DART API 키 list resolve — gather DartFetchProvider 위임.

    Requires: ``dartlab.gather.dart.keys`` (env DART_API_KEY/DART_API_KEYS + .env).
    Raises: RuntimeError — DartFetchProvider 미등록.
    Example:
        >>> resolveDartKeys()  # doctest: +SKIP
    """
    return _provider().resolveKeys(apiKey=apiKey, apiKeys=apiKeys)


def hasDartApiKey() -> bool:
    """DART API 키 설정 여부 — gather DartFetchProvider 위임.

    Requires: ``dartlab.gather.dart.keys``.
    Raises: RuntimeError — DartFetchProvider 미등록.
    Example:
        >>> hasDartApiKey()  # doctest: +SKIP
    """
    return _provider().hasKey()
