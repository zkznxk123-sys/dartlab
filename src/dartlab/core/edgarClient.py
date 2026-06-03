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

import polars as pl

DEFAULT_USER_AGENT = "DartLab eddmpython@gmail.com"
DEFAULT_BASE_URL = "https://data.sec.gov"
DEFAULT_SEC_URL = "https://www.sec.gov"

# 정기공시 form 종류 — fetch(filter)·build·read 공유 상수.
SUPPORTED_REGULAR_FORMS = ("10-K", "10-Q", "20-F", "40-F")

# companyfacts normalize(gather facts.companyFactsToRows) → parquet(providers saver) 공유 schema.
EDGAR_COMPANYFACTS_SCHEMA = {
    "cik": pl.Utf8,
    "entityName": pl.Utf8,
    "namespace": pl.Utf8,
    "tag": pl.Utf8,
    "label": pl.Utf8,
    "unit": pl.Utf8,
    "val": pl.Float64,
    "fy": pl.Int32,
    "fp": pl.Utf8,
    "form": pl.Utf8,
    "filed": pl.Date,
    "frame": pl.Utf8,
    "start": pl.Date,
    "end": pl.Date,
    "accn": pl.Utf8,
}


class EdgarApiError(RuntimeError):
    """SEC API 호출 오류 (공유 infra 예외 — gather raise, providers except)."""


@runtime_checkable
class EdgarFetchProvider(Protocol):
    """EDGAR fetch+normalize 추상화 — providers build/read 가 gather/edgar 출력을 얻는 seam.

    EDGAR 는 SEC API fetch 와 JSON→DataFrame normalize 가 밀결합(companyFactsToRows 등)이라
    gather/edgar 가 Extract+normalize 를 전담한다. providers 의 parquet-build·accessor 가
    normalize 결과를 쓰려면 ``call(module, func, ...)`` 로 gather/edgar 서브모듈에 위임.
    """

    def makeClient(self, **kwargs: Any) -> Any:
        """SEC HTTP 클라이언트 인스턴스 생성 (userAgent/email/minInterval/timeout/maxRetries)."""
        ...

    def call(self, module: str, func: str, *args: Any, **kwargs: Any) -> Any:
        """gather/edgar.<module>.<func> 위임 호출 (fetch+normalize 출력)."""
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


# ── gather/edgar fetch+normalize 위임 delegate (providers 소비자 호환 seam) ──
# 소비자는 import 경로만 본 모듈로 교체. 실제 구현은 gather/edgar 서브모듈.


def _call(module: str, func: str, *args: Any, **kwargs: Any) -> Any:
    return _provider().call(module, func, *args, **kwargs)


def getSubmissionsJson(*args: Any, **kwargs: Any) -> Any:
    """SEC submissions JSON fetch — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> getSubmissionsJson("0000320193")  # doctest: +SKIP"""
    return _call("submissions", "getSubmissionsJson", *args, **kwargs)


def mergeSubmissionFilings(*args: Any, **kwargs: Any) -> Any:
    """submissions filing 배열 병합(paginated) — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> mergeSubmissionFilings(sub)  # doctest: +SKIP"""
    return _call("submissions", "mergeSubmissionFilings", *args, **kwargs)


def findRegularFilings(*args: Any, **kwargs: Any) -> Any:
    """정기공시 filing 필터/정규화 — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> findRegularFilings(sub)  # doctest: +SKIP"""
    return _call("submissions", "findRegularFilings", *args, **kwargs)


def filingsFrame(*args: Any, **kwargs: Any) -> Any:
    """filing list → DataFrame — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> filingsFrame(sub)  # doctest: +SKIP"""
    return _call("submissions", "filingsFrame", *args, **kwargs)


def getCompanyFactsJson(*args: Any, **kwargs: Any) -> Any:
    """SEC companyfacts JSON fetch — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> getCompanyFactsJson("0000320193")  # doctest: +SKIP"""
    return _call("facts", "getCompanyFactsJson", *args, **kwargs)


def getCompanyConceptJson(*args: Any, **kwargs: Any) -> Any:
    """SEC companyconcept JSON fetch — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> getCompanyConceptJson(...)  # doctest: +SKIP"""
    return _call("facts", "getCompanyConceptJson", *args, **kwargs)


def getFrameJson(*args: Any, **kwargs: Any) -> Any:
    """SEC frames JSON fetch — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> getFrameJson(...)  # doctest: +SKIP"""
    return _call("facts", "getFrameJson", *args, **kwargs)


def companyFactsToRows(*args: Any, **kwargs: Any) -> Any:
    """companyfacts JSON → flat DataFrame normalize — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> companyFactsToRows(payload)  # doctest: +SKIP"""
    return _call("facts", "companyFactsToRows", *args, **kwargs)


def loadTickers(*args: Any, **kwargs: Any) -> Any:
    """SEC company_tickers fetch+캐시 — gather/edgar 위임. Requires: gather.edgar. Raises: EdgarApiError. Example: >>> loadTickers()  # doctest: +SKIP"""
    return _call("identity", "loadTickers", *args, **kwargs)


def resolveIssuer(*args: Any, **kwargs: Any) -> Any:
    """ticker/CIK → issuer dict — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> resolveIssuer("AAPL")  # doctest: +SKIP"""
    return _call("identity", "resolveIssuer", *args, **kwargs)


def searchIssuers(*args: Any, **kwargs: Any) -> Any:
    """issuer 검색 DataFrame — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> searchIssuers("apple")  # doctest: +SKIP"""
    return _call("identity", "searchIssuers", *args, **kwargs)


def iterIssuers(*args: Any, **kwargs: Any) -> Any:
    """issuer 검색 iterator — gather/edgar 위임. Requires: gather.edgar. Raises: 없음. Example: >>> list(iterIssuers("apple"))  # doctest: +SKIP"""
    return _call("identity", "iterIssuers", *args, **kwargs)
