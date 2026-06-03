"""EDGAR/SEC fetch seam — DI Protocol (정공법 B).

gather 가 모든 EDGAR network fetch 를 전담(ETL Extract). providers 의 build/read
코드가 client 가 필요하면 본 core seam 으로 접근 — providers↛gather 단방향 유지.
``gather/edgar/client.py`` 의 ``EdgarFetchProvider`` 구현이 import 시점에 register.

``EdgarApiError`` + ``DEFAULT_*`` URL/User-Agent 는 build·fetch 양쪽이 쓰는 공유
식별자/상수라 core 에 정의 (gather raise/fetch, providers except/URL 조립). 본 모듈의
``EdgarClient`` 는 *factory 함수* — 소비자 호출부(``EdgarClient(...)``)는 그대로 두고
import 경로만 본 모듈로 교체.

CredentialProvider/LoaderProvider/DartFetchProvider 와 동일 패턴.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

DEFAULT_USER_AGENT = "DartLab eddmpython@gmail.com"
DEFAULT_BASE_URL = "https://data.sec.gov"
DEFAULT_SEC_URL = "https://www.sec.gov"


class EdgarApiError(RuntimeError):
    """SEC API 호출 오류 (공유 infra 예외 — gather raise, providers except)."""


@runtime_checkable
class EdgarFetchProvider(Protocol):
    """EDGAR fetch 추상화 — providers build/read 가 client 를 얻는 seam."""

    def makeClient(self, **kwargs: Any) -> Any:
        """SEC HTTP 클라이언트 인스턴스 생성 (userAgent/email/minInterval/timeout/maxRetries)."""
        ...


_PROVIDER: EdgarFetchProvider | None = None

_KNOWN_PROVIDER_MODULES: tuple[str, ...] = ("dartlab.gather.edgar.client",)
_DISCOVERED = False


def _discover() -> None:
    """알려진 EdgarFetchProvider 모듈을 한 번만 lazy import — register 트리거."""
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


def registerEdgarFetchProvider(provider: EdgarFetchProvider) -> None:
    """EdgarFetchProvider 등록 — gather/edgar/client 가 import 시점에 호출."""
    global _PROVIDER
    _PROVIDER = provider


def getEdgarFetchProvider() -> EdgarFetchProvider | None:
    """현재 등록된 EdgarFetchProvider 반환. 미등록이면 None. auto-discovery 트리거."""
    _discover()
    return _PROVIDER


def _provider() -> EdgarFetchProvider:
    provider = getEdgarFetchProvider()
    if provider is None:
        raise RuntimeError("EdgarFetchProvider 미등록 — dartlab.gather.edgar.client import 실패 (gather 미설치/오류)")
    return provider


def EdgarClient(
    *,
    userAgent: str | None = None,
    email: str | None = None,
    minInterval: float = 0.2,
    timeout: float = 30.0,
    maxRetries: int = 3,
) -> Any:
    """SEC EDGAR 클라이언트 factory — gather EdgarFetchProvider 위임.

    Requires: ``dartlab.gather.edgar.client`` (EdgarFetchProvider 등록). SEC public API
        는 키 불요, User-Agent 필수(_buildUserAgent 자동).
    Raises: RuntimeError — EdgarFetchProvider 미등록.
    Example:
        >>> from dartlab.core.edgarClient import EdgarClient  # doctest: +SKIP
        >>> client = EdgarClient()
    """
    return _provider().makeClient(
        userAgent=userAgent,
        email=email,
        minInterval=minInterval,
        timeout=timeout,
        maxRetries=maxRetries,
    )
