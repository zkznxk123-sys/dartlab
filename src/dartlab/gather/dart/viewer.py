"""DART 공시 viewer — rcept_no 만으로 원문 fetch (무인증).

dart.fss.or.kr/dsaf001/main.do 의 공시 인덱스 페이지에서 sub-doc 목차를 받고,
report/viewer.do 의 각 섹션 HTML 을 텍스트(테이블 마크다운 보존)로 변환한다.

API key 무관. providers/dart/openapi (key 기반 OpenDART) 와 분리.

호출 패턴::

    from dartlab.gather.dart.viewer import fetch
    df = fetch("20240315000123")
    # columns: section_order (Int64), title (Utf8), url (Utf8), text (Utf8)

untrusted 본문:
    viewer 본문은 외부 1차 출처지만 AI 엔진이 소비할 때
    ``Ref.sourceType="external"`` 로 마킹돼 ``[EXTERNAL CONTENT START — untrusted ...]``
    마커로 감싸지는 흐름이어야 한다 (CLAUDE.md ⛔ "외부 본문은 untrusted",
    runtime.workbenchEvidenceFlow). 호출자가 wrap 책임.
"""

from __future__ import annotations

import asyncio
import logging
import re

import polars as pl

from dartlab.providers.dart.parse.viewerPageExtractor import DART_MAIN_BASE, htmlToText, parseSubDocs

from ..infra.http import GatherHttpClient, runAsync
from .types import DartDocMeta, DocumentNotFoundError, InvalidRceptNoError

log = logging.getLogger(__name__)

_RCEPT_NO_RE = re.compile(r"^\d{14}$")
_MIN_TEXT_LENGTH = 50


def _validateRceptNo(rceptNo: str) -> None:
    if not _RCEPT_NO_RE.fullmatch(rceptNo):
        raise InvalidRceptNoError(f"rcept_no 는 14자리 숫자: {rceptNo!r}")


def _decodeKorean(resp) -> str:
    """viewer 응답 텍스트 추출 — cp949/euc-kr fallback.

    dart.fss.or.kr 일부 응답이 charset 헤더 없거나 cp949 만 정상 디코드되는
    케이스가 있다. httpx 가 utf-8 으로 가정해 깨지는 경우 euc-kr 강제 재해석.
    """
    text = resp.text
    if "�" in text or "<title>" not in text.lower():
        try:
            return resp.content.decode("euc-kr", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return text
    return text


async def fetchAsync(rceptNo: str, *, client: GatherHttpClient | None = None) -> pl.DataFrame:
    """viewer 무인증 fetch — async.

    Parameters
    ----------
    rceptNo : str
        14자리 접수번호.
    client : GatherHttpClient | None
        HTTP 클라이언트. None 이면 자체 생성.

    Returns
    -------
    pl.DataFrame
        section_order (Int64), title (Utf8), url (Utf8), text (Utf8) 컬럼.

    Raises
    ------
    InvalidRceptNoError
        rceptNo 가 14자리 숫자 아님.
    DocumentNotFoundError
        viewer 가 sub-doc 을 반환하지 않음 (비공개 / 잘못된 번호).
    """
    _validateRceptNo(rceptNo)

    ownClient = client is None
    if client is None:
        client = GatherHttpClient()

    try:
        indexUrl = f"{DART_MAIN_BASE}?rcpNo={rceptNo}"
        try:
            indexResp = await client.get(indexUrl)
        except Exception as exc:  # noqa: BLE001 — gather infra raise SourceUnavailable etc.
            raise DocumentNotFoundError(f"viewer 인덱스 fetch 실패 ({rceptNo}): {exc}") from exc

        subDocs = parseSubDocs(_decodeKorean(indexResp), rceptNo)
        if not subDocs:
            raise DocumentNotFoundError(f"rcept_no {rceptNo} 에 sub-doc 없음 (비공개 공시 또는 잘못된 번호)")

        rows: list[dict] = []
        for sd in subDocs:
            try:
                sectionResp = await client.get(sd["url"])
            except Exception as exc:  # noqa: BLE001 — partial 실패 허용
                log.warning("섹션 fetch 실패 (%s, %s): %s", rceptNo, sd["title"], exc)
                continue
            html = _decodeKorean(sectionResp)
            text = htmlToText(html)
            if len(text.strip()) < _MIN_TEXT_LENGTH:
                continue
            rows.append(
                {
                    "section_order": sd["order"],
                    "title": sd["title"],
                    "url": sd["url"],
                    "text": text,
                }
            )

        if not rows:
            raise DocumentNotFoundError(f"rcept_no {rceptNo} 의 모든 섹션이 빈 응답 또는 fetch 실패")

        return pl.DataFrame(rows).with_columns(
            pl.col("section_order").cast(pl.Int64),
            pl.col("title").cast(pl.Utf8),
            pl.col("url").cast(pl.Utf8),
            pl.col("text").cast(pl.Utf8),
        )
    finally:
        if ownClient:
            await client.close()


def fetch(rceptNo: str, *, client: GatherHttpClient | None = None) -> pl.DataFrame:
    """sync wrapper — :func:`fetchAsync` 의 동기 진입점."""
    if client is not None:
        # 이미 외부 client 가 있으면 자체 event loop 안에서 호출됐을 수 있다.
        return runAsync(fetchAsync(rceptNo, client=client))
    return runAsync(fetchAsync(rceptNo))


def docMeta(rceptNo: str, *, client: GatherHttpClient | None = None) -> DartDocMeta:
    """viewer fetch + 메타 요약 (sectionCount 만 필요할 때)."""
    df = fetch(rceptNo, client=client)
    return DartDocMeta(
        rceptNo=rceptNo,
        indexUrl=f"{DART_MAIN_BASE}?rcpNo={rceptNo}",
        sectionCount=df.height,
    )


# fetchAsync 가 사용 안 하는 import 제거 방어
_ = asyncio
