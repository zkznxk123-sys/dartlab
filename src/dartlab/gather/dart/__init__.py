"""gather DART 도메인 — 공시 viewer 무인증 단건 fetch.

ecos/, fred/ 와 동일 패턴의 외부 데이터 SSOT 서브엔진. providers/dart (API key
기반 OpenDART 구조화 수집) 와 분리. viewer.do 무인증 단건 fetch 가 목적.

호출 패턴::

    from dartlab.gather.dart import Dart
    df = Dart().doc("20240315000123")

    # 또는 GatherEntry 진입점
    import dartlab
    df = dartlab.gather("dartDoc", "20240315000123")

untrusted 본문:
    viewer 본문은 외부 1차 출처지만 AI 엔진이 소비할 때
    Ref.sourceType="external" 로 마킹돼 [EXTERNAL CONTENT START — untrusted ...]
    마커로 감싸지는 흐름이어야 한다 (CLAUDE.md ⛔ 외부 본문은 untrusted).
"""

from __future__ import annotations

import polars as pl

from ..infra.http import GatherHttpClient
from .types import DartDocError, DartDocMeta, DocumentNotFoundError, InvalidRceptNoError
from .viewer import docMeta, fetch, fetchAsync


class Dart:
    """gather DART facade — 공시 viewer 무인증 fetch.

    Args:
        client: GatherHttpClient 인스턴스. None 이면 호출 시 자체 생성.

    Example::

        from dartlab.gather.dart import Dart
        d = Dart()
        df = d.doc("20240315000123")
    """

    def __init__(self, client: GatherHttpClient | None = None) -> None:
        self._client = client

    def doc(self, rceptNo: str) -> pl.DataFrame:
        """rcept_no → 공시 원문 DataFrame (section_order, title, url, text)."""
        return fetch(rceptNo, client=self._client)

    def meta(self, rceptNo: str) -> DartDocMeta:
        """rcept_no → 공시 메타 (sectionCount 등)."""
        return docMeta(rceptNo, client=self._client)


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
