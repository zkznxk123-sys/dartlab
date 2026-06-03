"""DART OpenAPI 클라이언트.

from dartlab import OpenDart

d = OpenDart()
s = d("삼성전자")

s.finance(2020)                         # 2020~현재 Q1~Q4
s.report("배당", 2020)                  # 배당 2020~현재
s.filings("2024")                       # 공시
s.info()                                # 개황
s.shares()                              # 지분공시
s.saveFinance("재무.csv", 2020, kr=True) # 한글 컬럼 저장
호환 alias:
    from dartlab import Dart

NOTE: Dart/OpenDart 파사드·ZipDocsCollector·korColumns 는 lazy ``__getattr__`` 노출 —
build(``build.saver``→``core.dartConstants``) ↔ facade 순환 import 회피. DartClient·키·
DartApiError 는 gather fetch 전담(core.dartClient seam). zip 병렬 fetch 는 gather.dart.document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# core 재노출(경량) — gather 가 fetch 전담, providers 소비자 호환용 seam.
from dartlab.core.dartClient import DartApiError, DartClient

if TYPE_CHECKING:
    from dartlab.providers.dart.build.saver import korColumns
    from dartlab.providers.dart.openapi.dart import Dart, DartCompany, OpenDart, OpenDartCompany
    from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector

__all__ = [
    "OpenDart",
    "OpenDartCompany",
    "Dart",
    "DartCompany",
    "DartClient",
    "DartApiError",
    "ZipDocsCollector",
    "korColumns",
]

_LAZY: dict[str, str] = {
    "OpenDart": "dartlab.providers.dart.openapi.dart",
    "OpenDartCompany": "dartlab.providers.dart.openapi.dart",
    "Dart": "dartlab.providers.dart.openapi.dart",
    "DartCompany": "dartlab.providers.dart.openapi.dart",
    "ZipDocsCollector": "dartlab.providers.dart.openapi.zipCollector",
    "korColumns": "dartlab.providers.dart.build.saver",
}


def __getattr__(name: str):
    """lazy re-export — facade/collector/korColumns 를 접근 시점에만 import (순환 회피)."""
    import importlib

    modPath = _LAZY.get(name)
    if modPath is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(modPath), name)
