"""gather DART 도메인 — 공시 viewer 무인증 단건 fetch.

ecos/, fred/ 와 동일 패턴의 외부 데이터 SSOT 서브엔진. providers/dart (API key
기반 OpenDART 구조화 수집) 와 분리. viewer.do 무인증 단건 fetch 가 목적.

호출 패턴::

    from dartlab.gather.dart import Dart
    df = Dart().doc("20240315000123")

untrusted 본문:
    viewer 본문은 외부 1차 출처지만 호출자가 외부 untrusted 마커로 감싸는 책임.
"""

from __future__ import annotations

from .facade import Dart
from .types import DartDocError, DartDocMeta, DocumentNotFoundError, InvalidRceptNoError
from .viewer import docMeta, fetch, fetchAsync

__all__ = [
    "Dart",
    "DartDocError",
    "DartDocMeta",
    "DocumentNotFoundError",
    "InvalidRceptNoError",
    "docMeta",
    "fetch",
    "fetchAsync",
]
