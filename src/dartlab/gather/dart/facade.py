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

        Capabilities: 14 자리 rcept_no → viewer.fetch 위임 → sub-doc 본문 long DataFrame.
        AIContext: gather("dartDoc", ...) entry handler 의 backend — untrusted external 본문.
        Guide: 무인증 (DART_API_KEY 불필요) — viewer URL 직접 fetch.
        When: 단일 공시 원문 분석 (텍스트 추출 / 변경 비교) 시.
        How: viewer.fetch(rceptNo, client) → BeautifulSoup → sub-doc 목차 + text.

        Args:
            rceptNo: 14자리 접수번호.

        Returns:
            DataFrame ``(section_order, title, url, text)`` — 각 sub-doc 섹션.

        Raises:
            InvalidRceptNoError: rceptNo 가 14자리 숫자 아님.
            DocumentNotFoundError: viewer 가 sub-doc 을 반환하지 않음.

        Requires:
            네트워크 (``dart.fss.or.kr/dsaf001/main.do``). DART_API_KEY 불필요.

        Example:
            >>> d = Dart()
            >>> df = d.doc("20240315000123")

        See Also:
            meta : 본 공시의 메타 정보만 추출.
            viewer.fetch : 위임 대상.
            entry/handlers.handleDartDoc : 사용자 진입점 (gather('dartDoc', ...)).
        """
        return fetch(rceptNo, client=self._client)

    def meta(self, rceptNo: str) -> DartDocMeta:
        """rcept_no → 공시 메타 (sectionCount 등).

        Capabilities: 14 자리 rcept_no → viewer.docMeta 위임 → DartDocMeta (target_no).
        AIContext: 본문 fetch 전 sub-doc 개수 확인 / 인덱스 URL 검증 진입.
        Guide: 본문 없이 메타만 — 본문 필요 시 doc() 사용.
        When: 공시 카운트만 필요 / fetch 전 size 확인 시.
        How: viewer.docMeta(rceptNo) → DartDocMeta named tuple.

        Args:
            rceptNo: 14자리 접수번호.

        Returns:
            DartDocMeta ``(rceptNo, indexUrl, sectionCount)``.

        Raises:
            InvalidRceptNoError: rceptNo 가 14자리 숫자 아님.
            DocumentNotFoundError: viewer 가 sub-doc 을 반환하지 않음.

        Requires:
            네트워크 (``dart.fss.or.kr``). DART_API_KEY 불필요.

        Example:
            >>> d = Dart()
            >>> m = d.meta("20240315000123")

        See Also:
            doc : 본문까지 추출.
            viewer.docMeta : 위임 대상.
        """
        return docMeta(rceptNo, client=self._client)


__all__ = ["Dart"]
