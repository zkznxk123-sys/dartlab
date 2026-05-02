"""Request-scoped Company 인스턴스 캐시.

한 요청(/api/ask 1회 · `dartlab.ask()` 1회)안에서 같은 ``stockCode`` 로 접근하는
모든 tool (``analysis``, ``credit``, ``debt``, ``capital``, ``governance``,
``audit``, ``show`` 등) 이 **같은 Company 인스턴스를 공유**하게 한다.

현재 `ai/tools/__init__.py::_buildHandler._companyHandler` 는 tool 호출마다
``dartlab.Company(stockCode)`` 를 **매번 새로 생성**해서 finance parquet 로드 +
매핑이 반복되고, 각 Company 가 독립 `BoundedCache(max_entries=30)` 를 갖기 때문에
캐시 격리로 인해 같은 데이터를 여러 번 디스크에서 읽는다. 여기에 Polars 네이티브
힙이 쌓여 `BoundedCache FATAL` 방출이 반복되어 finance parquet 을 다시 로드하는
악순환이 발생한다.

해법: ``contextvars.ContextVar`` 를 써서 요청 시작 시 ``{stockCode: Company}``
dict 를 context 에 바인딩하고, ``_companyHandler`` 가 ``getOrCreateCompany`` 로
이 dict 에서 인스턴스를 찾아 재사용. 요청 종료 시 ``endRequest`` 가 dict 를
비우고 ``gc.collect`` 를 촉발한다 (Polars heap 방출 보조).

Notebook / CLI 등 ctx 가 없는 환경에서는 ``getOrCreateCompany`` 가 매번 새 인스턴스를
반환 — 기존 동작과 동일. 영향 0.

설계는 ``ai/runtime/progressCapture.py`` 와 같은 ContextVar 패턴을 따른다.
"""

from __future__ import annotations

import contextvars
from typing import Any, Optional

_companyCache: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "dartlab_companyCache", default=None
)


def _normalizeStockCode(raw: str) -> str:
    """Company cache key 정규화.

    - 대문자 (US ticker)
    - 숫자만이면 6자리 zero-pad (KR)
    - 공백 strip
    """
    if raw is None:
        return ""
    s = str(raw).strip().upper()
    if s.isdigit():
        s = s.zfill(6)
    return s


def beginRequest() -> dict[str, Any]:
    """요청 시작 시 호출. 빈 dict 를 ctx 에 바인딩해 반환.

    이미 바인딩된 dict 가 있으면 그걸 반환 (nested 호출 허용).
    """
    existing = _companyCache.get()
    if isinstance(existing, dict):
        return existing
    d: dict[str, Any] = {}
    _companyCache.set(d)
    return d


def endRequest(d: dict[str, Any] | None = None) -> None:
    """요청 종료 시 호출. dict clear + ctx 에서 분리 + gc 촉발.

    Polars DataFrame 이 Rust heap 에 있어 파이썬 참조 해제로는 즉시 회수되지
    않지만, ``gc.collect`` 가 참조 순환 끊은 뒤 Polars 측 Drop 이 호출될 여지를
    준다. 실패해도 무시.
    """
    target = d if d is not None else _companyCache.get()
    if isinstance(target, dict):
        target.clear()
    _companyCache.set(None)
    try:
        import gc

        gc.collect()
    except Exception:  # noqa: BLE001
        pass


def getOrCreateCompany(stockCode: str) -> Any:
    """현재 ctx 에 cache 가 있으면 재사용, 없으면 일회성 Company 생성.

    - ctx 있음 + cache HIT → 저장된 인스턴스 반환 (finance 매핑 재수행 無)
    - ctx 있음 + cache MISS → ``dartlab.Company(stockCode)`` 생성 후 push → 반환
    - ctx 없음 → 그냥 ``dartlab.Company(stockCode)`` 반환 (라이브러리/노트북 사용자 영향 0)
    """
    import dartlab

    key = _normalizeStockCode(stockCode)
    cache = _companyCache.get()
    if cache is None:
        return dartlab.Company(stockCode)
    if key in cache:
        return cache[key]
    company = dartlab.Company(stockCode)
    cache[key] = company
    return company


def peekCache() -> dict[str, Any] | None:
    """디버그/테스트 용 — 현재 ctx 의 cache dict 참조. 없으면 None."""
    return _companyCache.get()


__all__ = [
    "beginRequest",
    "endRequest",
    "getOrCreateCompany",
    "peekCache",
]
