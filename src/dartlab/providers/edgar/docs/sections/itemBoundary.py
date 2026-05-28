"""EDGAR filing 1 개 → section row list 변환 — plan delegated-prancing-tower PR-E2.

``_splitItems`` 결과 (markdown item list) + filing-level raw HTML 을 받아 sections
artifact 의 row dict list 로 변환. 각 row 의 schema:

    topic / blockType / blockOrder / textNodeType / textLevel / textPath /
    content_raw / content_plain + filing meta (accession_no/filing_date/...)

contentRaw 는 filing-level outerHTML (sanitized) — 모든 row 가 공유 (parquet dict
encoding 으로 사이즈 흡수). viewer / table_struct path 가 raw HTML 단편 접근.
contentPlain 은 row-level markdown (text/table 분리 후 별도).
"""

from __future__ import annotations

import re
from typing import Any

import polars as pl  # noqa: F401  (caller 가 schema 동일 dict 입력 가정 — type 힌트 reuse)

from dartlab.providers.edgar.docs.sections.mapper import mapSectionTitle
from dartlab.providers.edgar.docs.sections.textStructure import parseTextStructure


# 옛 pipeline._splitTextTable 의 동치 — markdown text 와 markdown table 분리.
# 본 PR-E2 후 옛 pipeline 의 본 helper 는 PR-E7 폐기 시 제거.
def splitTextTable(content: str) -> tuple[str, str]:
    """markdown content 를 텍스트 부분과 테이블 부분으로 분리.

    옛 ``providers/edgar/docs/sections/pipeline.py::_splitTextTable`` 동치.

    Args:
        content: markdown 본문.

    Returns:
        (텍스트, 표) 튜플. 표 없으면 ("", "").

    Raises:
        없음.

    Example:
        >>> splitTextTable("para\\n| a | b |\\n| --- | --- |\\n| 1 | 2 |")
        ('para', '| a | b |\\n| --- | --- |\\n| 1 | 2 |')
    """
    textLines: list[str] = []
    tableLines: list[str] = []
    for line in content.split("\n"):
        if line.strip().startswith("|"):
            tableLines.append(line)
        else:
            textLines.append(line)
    return "\n".join(textLines).strip(), "\n".join(tableLines).strip()


_IX_DECOMPOSE_RE = re.compile(r"<(ix:header|ix:hidden|ix:references|ix:resources|xbrli:|dei:|link:)", re.IGNORECASE)


def sanitizeRawHtml(html: str) -> str:
    """filing raw HTML 을 viewer 안전 양식으로 sanitize.

    BeautifulSoup decompose 양식 — script/style/meta/link/header/footer/nav 제거.
    ``<ix:*>`` 도 unwrap. 표 (``<table>``) 의 ALIGN/rowspan/colspan/COLGROUP 은 그대로
    보존 — viewer 시각 fidelity 핵심.

    옛 ``_htmlToText`` ([fetchHtmlParse.py:225-255](src/dartlab/providers/edgar/docs/fetchHtmlParse.py#L225-L255))
    의 decompose 룰과 동일. 단 본 함수는 표 → markdown 변환 *전* 단계에서 중단해
    raw HTML 그대로 emit.

    Args:
        html: filing 원본 iXBRL HTML.

    Returns:
        sanitized HTML — 노이즈 태그 제거됐지만 표 구조 + 본문 layout 보존.

    Raises:
        없음.

    Example:
        >>> sanitized = sanitizeRawHtml(rawHtml)  # doctest: +SKIP
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "meta", "link", "header", "footer", "nav"]):
        tag.decompose()
    # display:none / visibility:hidden style 제거 — viewer 표시 무의미.
    for tag in soup.find_all(style=True):
        attrs = getattr(tag, "attrs", None)
        if not attrs:
            continue
        style = str(attrs.get("style") or "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()
    # ix:* (inline XBRL) — decompose 또는 unwrap.
    for tag in soup.find_all(re.compile(r"^(ix:header|ix:hidden|ix:references|ix:resources|xbrli:|dei:|link:)")):
        tag.decompose()
    for tag in soup.find_all(re.compile(r"^ix:")):
        tag.unwrap()
    return str(soup.body or soup)


def extractItemChunks(
    items: list[dict],
    rawHtml: str,
    formType: str,
    meta: dict[str, Any],
) -> list[dict]:
    """filing 1 개의 item list → sections artifact row dict list.

    각 item 의 markdown content 를 (text, table) 로 분리 + text 부분에
    ``parseTextStructure`` 적용해 heading/body 별 row 생성. table 부분은 별도 row.
    모든 row 가 filing-level ``content_raw`` 공유.

    Args:
        items: ``_splitItems`` 결과 ``[{"title": str, "content": str}]``.
        rawHtml: filing 원본 HTML (``sanitizeRawHtml`` 결과 권장).
        formType: ``"10-K"`` / ``"10-Q"`` / ``"20-F"`` / ``"40-F"``.
        meta: filing-level meta — ``cik`` / ``accession_no`` / ``filing_date`` /
            ``period_end`` / ``filing_url`` / ``ticker`` / ``year`` / ``period_key``.

    Returns:
        section row dict list. 각 row 의 key:
        - ``topic``, ``blockType``, ``blockOrder``, ``textNodeType``, ``textLevel``, ``textPath``
        - ``content_raw`` (filing-level 공유), ``content_plain`` (row-level)
        - meta keys (filing 단위 denormalized)

    Raises:
        없음.

    Example:
        >>> rows = extractItemChunks(items, raw, "10-K", meta)  # doctest: +SKIP
    """
    rawSanitized = sanitizeRawHtml(rawHtml)
    out: list[dict] = []
    blockOrderCounter = 0
    for item in items:
        rawTitle = str(item.get("title") or "")
        content = str(item.get("content") or "")
        if not rawTitle or not content:
            continue
        topic = mapSectionTitle(formType, rawTitle)
        textPart, tablePart = splitTextTable(content)

        if textPart:
            structured = parseTextStructure(textPart, topic=topic)
            if not structured:
                out.append(
                    _makeRow(
                        topic=topic,
                        blockType="text",
                        blockOrder=blockOrderCounter,
                        textNodeType="body",
                        textLevel=0,
                        textPath=None,
                        contentRaw=rawSanitized,
                        contentPlain=textPart,
                        sourceTitle=rawTitle,
                        meta=meta,
                    )
                )
                blockOrderCounter += 1
            else:
                for s in structured:
                    out.append(
                        _makeRow(
                            topic=topic,
                            blockType="text",
                            blockOrder=blockOrderCounter,
                            textNodeType=s.get("textNodeType"),
                            textLevel=s.get("textLevel"),
                            textPath=s.get("textPath"),
                            contentRaw=rawSanitized,
                            contentPlain=s.get("text") or "",
                            sourceTitle=rawTitle,
                            meta=meta,
                        )
                    )
                    blockOrderCounter += 1
        if tablePart:
            out.append(
                _makeRow(
                    topic=topic,
                    blockType="table",
                    blockOrder=blockOrderCounter,
                    textNodeType=None,
                    textLevel=None,
                    textPath=None,
                    contentRaw=rawSanitized,
                    contentPlain=tablePart,
                    sourceTitle=rawTitle,
                    meta=meta,
                )
            )
            blockOrderCounter += 1
    return out


def _makeRow(
    *,
    topic: str,
    blockType: str,
    blockOrder: int,
    textNodeType: str | None,
    textLevel: int | None,
    textPath: str | None,
    contentRaw: str,
    contentPlain: str,
    sourceTitle: str,
    meta: dict[str, Any],
) -> dict:
    """sections artifact row dict 생성 — schema 통일."""
    return {
        "topic": topic,
        "blockType": blockType,
        "blockOrder": blockOrder,
        "textNodeType": textNodeType,
        "textLevel": textLevel,
        "textPath": textPath,
        "content_raw": contentRaw,
        "content_plain": contentPlain,
        "source_title": sourceTitle,
        # filing meta (denormalized — parquet dict encoding)
        "ticker": str(meta.get("ticker") or ""),
        "cik": str(meta.get("cik") or ""),
        "accession_no": str(meta.get("accession_no") or ""),
        "filing_date": meta.get("filing_date"),
        "period_end": meta.get("period_end"),
        "form_type": str(meta.get("form_type") or ""),
        "report_type": str(meta.get("report_type") or ""),
        "period_key": str(meta.get("period_key") or ""),
        "filing_url": str(meta.get("filing_url") or ""),
        "year": meta.get("year"),
    }
