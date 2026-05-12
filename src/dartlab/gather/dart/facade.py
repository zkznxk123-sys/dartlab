"""gather DART facade — Dart 클래스 본체.

`__init__.py` 의 thin facade 룰 (룰 4) 을 위해 클래스 정의 분리. 호출자는
`from dartlab.gather.dart import Dart` 그대로 사용 (`__init__` 가 re-export).
"""

from __future__ import annotations

import polars as pl

from ..infra.http import GatherHttpClient
from .types import DartDocMeta
from .viewer import docMeta, fetch


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
        """rcept_no → 공시 원문 DataFrame.

        Args:
            rceptNo: 14자리 접수번호.

        Returns:
            DataFrame ``(section_order, title, url, text)`` — 각 sub-doc 섹션.

        Raises:
            InvalidRceptNoError: rceptNo 가 14자리 숫자 아님.
            DocumentNotFoundError: viewer 가 sub-doc 을 반환하지 않음.

        Example:
            >>> d = Dart()
            >>> df = d.doc("20240315000123")
        """
        return fetch(rceptNo, client=self._client)

    def meta(self, rceptNo: str) -> DartDocMeta:
        """rcept_no → 공시 메타 (sectionCount 등).

        Args:
            rceptNo: 14자리 접수번호.

        Returns:
            DartDocMeta ``(rceptNo, indexUrl, sectionCount)``.

        Raises:
            InvalidRceptNoError: rceptNo 가 14자리 숫자 아님.
            DocumentNotFoundError: viewer 가 sub-doc 을 반환하지 않음.

        Example:
            >>> d = Dart()
            >>> m = d.meta("20240315000123")
        """
        return docMeta(rceptNo, client=self._client)


__all__ = ["Dart"]
