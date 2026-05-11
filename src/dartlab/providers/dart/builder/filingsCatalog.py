"""DART Company 의 공시 메타·원문 조회 backend.

Company.filings / update / disclosure / liveFilings / readFiling 5 진입점은
DART API + 로컬 parquet 의 공시 메타데이터 + ZIP 원문 처리. Company facade 가
본 모듈의 build* 함수에 thin delegate.

Module-level builders:
    buildFilings      — 로컬 보유 공시 목록 (parquet)
    buildUpdate       — 누락 공시 증분 수집
    buildDisclosure   — OpenDART 공시 목록 (단일 종목)
    buildLiveFilings  — OpenDART 실시간 공시 (정규화)
    buildReadFiling   — 공시 원문 텍스트 / ZIP 섹션
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.core.dataLoader import DART_VIEWER, loadData
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.filingHelpers import filingRecord, filterFilingsByKeyword, resolveDateWindow, truncateText

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


_RCEPT_NO_PATTERN = re.compile(r"[?&]rcpNo=(\d{14})")


# ── filings (로컬 parquet) ───────────────────────────────────────


def buildFilings(company: Company) -> pl.DataFrame | None:
    """이 종목의 공시 문서 목록 + DART 뷰어 링크 (로컬 parquet).

    Args:
        company: Company 인스턴스.

    Returns:
        ``year/rceptDate/rceptNo/reportType/dartUrl`` 컬럼 DataFrame.
        docs 부재 시 빈 schema DataFrame.

    Raises:
        없음.

    Example:
        >>> buildFilings(c).head()
    """
    if not company._hasDocs:
        return pl.DataFrame(
            schema={
                "year": pl.Utf8,
                "rceptDate": pl.Utf8,
                "rceptNo": pl.Utf8,
                "reportType": pl.Utf8,
                "dartUrl": pl.Utf8,
            }
        )
    df = loadData(company.stockCode)
    docs = (
        df.select("year", "rcept_date", "rcept_no", "report_type")
        .unique(subset=["rcept_no"])
        .with_columns(
            pl.lit(DART_VIEWER).add(pl.col("rcept_no")).alias("dartUrl"),
        )
        .rename(
            {
                "report_type": "reportType",
                "rcept_date": "rceptDate",
                "rcept_no": "rceptNo",
            }
        )
        .sort("year", "rceptDate", descending=[True, True])
    )
    return docs


# ── update (증분 수집) ───────────────────────────────────────────


def buildUpdate(company: Company, *, categories: list[str] | None = None) -> dict[str, int]:
    """누락된 최신 공시를 증분 수집.

    Args:
        company: Company 인스턴스.
        categories: 수집 카테고리 (None 이면 전체).

    Returns:
        ``{category: count}`` 수집 통계 dict.

    Raises:
        없음 (OpenDART 호출 실패는 ``collectMissing`` 내부 처리).

    Example:
        >>> buildUpdate(c, categories=["docs"])
    """
    from dartlab.providers.dart.openapi.freshness import collectMissing

    return collectMissing(company.stockCode, categories=categories)


# ── disclosure (OpenDART 공시 목록) ──────────────────────────────


def buildDisclosure(
    company: Company,
    start: str | None = None,
    end: str | None = None,
    *,
    days: int = 365,
    type: str | None = None,
    keyword: str | None = None,
    finalOnly: bool = False,
) -> pl.DataFrame:
    """OpenDART 단일 종목 공시 목록.

    Args:
        company: Company 인스턴스.
        start: 시작일 (YYYYMMDD).
        end: 종료일.
        days: 기간 (start/end 미지정 시).
        type: 공시 유형 코드 (A=정기, B=주요사항, ...).
        keyword: 키워드 필터.
        finalOnly: True 면 최종보고서만.

    Returns:
        공시 목록 DataFrame (빈 경우 빈 DataFrame).

    Raises:
        없음 (OpenDART 오류는 빈 DataFrame).

    Example:
        >>> buildDisclosure(c, days=90, type="A")
    """
    from dartlab.providers.dart.openapi.dart import Dart

    d = Dart()
    s = d(company.stockCode)
    df = s.filings(start, end, type=type, final=finalOnly)
    if df.is_empty():
        return df
    if keyword:
        df = filterFilingsByKeyword(df, keyword=keyword, columns=["report_nm", "corp_name", "flr_nm"])
    return df


# ── liveFilings (정규화 실시간) ──────────────────────────────────


def buildLiveFilings(
    company: Company,
    start: str | None = None,
    end: str | None = None,
    *,
    days: int | None = None,
    limit: int = 20,
    keyword: str | None = None,
    forms: list[str] | tuple[str, ...] | None = None,
    finalOnly: bool = False,
) -> pl.DataFrame:
    """OpenDART 실시간 공시 정규화 (``docId/filedAt/title/formType/...``).

    ``forms`` 인자는 DART 에 forms 개념이 없어 무시 — liveFilings public API 시그니처
    호환 위해 유지.

    Args:
        company: Company 인스턴스.
        start: 시작일.
        end: 종료일.
        days: 기간.
        limit: 최대 행 수.
        keyword: 키워드 필터.
        forms: form 유형 리스트 (DART 무시).
        finalOnly: 최종본만.

    Returns:
        정규화된 공시 DataFrame (BoundedCache 결과).

    Raises:
        없음.

    Example:
        >>> buildLiveFilings(c, days=30, limit=10)
    """
    del forms

    startDate, endDate = resolveDateWindow(start, end, days=days)
    cacheKey = f"liveFilings:{startDate}:{endDate}:{limit}:{keyword}:{finalOnly}"
    if cacheKey in company._cache:
        return company._cache[cacheKey]

    from dartlab.core.messaging import progress
    from dartlab.providers.dart.openapi.dart import OpenDart

    progress(f"{company.corpName} 최신 공시 목록 조회 중... (OpenDART, {startDate}~{endDate})")
    df = OpenDart().filings(
        company.stockCode,
        startDate,
        endDate,
        final=finalOnly,
    )
    if isEmptyDf(df):
        result = pl.DataFrame(
            schema={
                "docId": pl.Utf8,
                "filedAt": pl.Utf8,
                "title": pl.Utf8,
                "formType": pl.Utf8,
                "docUrl": pl.Utf8,
                "indexUrl": pl.Utf8,
                "market": pl.Utf8,
                "corpName": pl.Utf8,
                "stockCode": pl.Utf8,
                "rceptNo": pl.Utf8,
                "reportNm": pl.Utf8,
                "viewerUrl": pl.Utf8,
                "corpCls": pl.Utf8,
            }
        )
        company._cache[cacheKey] = result
        return result

    normalized = (
        filterFilingsByKeyword(df, keyword=keyword, columns=["report_nm", "corp_name", "flr_nm"])
        .with_columns(
            [
                pl.col("rcept_no").cast(pl.Utf8).alias("docId"),
                pl.col("rcept_dt").cast(pl.Utf8).alias("filedAt"),
                pl.col("report_nm").cast(pl.Utf8).alias("title"),
                pl.col("report_nm").cast(pl.Utf8).alias("formType"),
                pl.lit(DART_VIEWER).add(pl.col("rcept_no").cast(pl.Utf8)).alias("docUrl"),
                pl.lit(DART_VIEWER).add(pl.col("rcept_no").cast(pl.Utf8)).alias("indexUrl"),
                pl.lit("KR").alias("market"),
                pl.col("corp_name").cast(pl.Utf8).alias("corpName"),
                pl.col("stock_code").cast(pl.Utf8).alias("stockCode"),
                pl.col("rcept_no").cast(pl.Utf8).alias("rceptNo"),
                pl.col("report_nm").cast(pl.Utf8).alias("reportNm"),
                pl.lit(DART_VIEWER).add(pl.col("rcept_no").cast(pl.Utf8)).alias("viewerUrl"),
                pl.col("corp_cls").cast(pl.Utf8).alias("corpCls"),
            ]
        )
        .select(
            [
                "docId",
                "filedAt",
                "title",
                "formType",
                "docUrl",
                "indexUrl",
                "market",
                "corpName",
                "stockCode",
                "rceptNo",
                "reportNm",
                "viewerUrl",
                "corpCls",
            ]
        )
    )
    result = normalized.head(limit) if limit > 0 else normalized
    company._cache[cacheKey] = result
    return result


# ── readFiling (원문 텍스트 / ZIP 섹션) ──────────────────────────


def buildReadFiling(
    company: Company,
    filing: Any,
    *,
    maxChars: int | None = None,
    sections: bool = False,
) -> dict[str, Any]:
    """접수번호 또는 ``liveFilings`` row 로 공시 원문 읽기.

    ``filing`` 이 14 자리 숫자면 직접 rceptNo. dict/Series 면 ``rceptNo``/``docId``/
    ``viewerUrl`` 키 추출. ``sections=True`` 면 ZIP 다운로드 + 섹션 파싱.

    Args:
        company: Company 인스턴스.
        filing: 14 자리 rceptNo str / liveFilings row dict / DART viewer URL.
        maxChars: 본문 최대 문자 (truncate).
        sections: True 면 ZIP 섹션 분리, False 면 텍스트 본문.

    Returns:
        ``{docId, market, title, docUrl, viewerUrl, ...}`` dict.

    Raises:
        ValueError: rceptNo 추출 실패 시.

    Example:
        >>> buildReadFiling(c, "20240315000123")
    """
    record = filingRecord(filing) or {}

    if isinstance(filing, str):
        text = filing.strip()
        if text.isdigit():
            rceptNo = text
            viewerUrl = f"{DART_VIEWER}{text}"
        else:
            match = _RCEPT_NO_PATTERN.search(text)
            rceptNo = match.group(1) if match else ""
            viewerUrl = text
    else:
        viewerUrl = str(record.get("viewerUrl") or record.get("docUrl") or "")
        rceptNo = str(record.get("rceptNo") or record.get("docId") or "")
        if not rceptNo and viewerUrl:
            match = _RCEPT_NO_PATTERN.search(viewerUrl)
            if match:
                rceptNo = match.group(1)

    if not rceptNo:
        raise ValueError("DART filing 읽기에는 rceptNo 또는 rcpNo가 포함된 viewer URL이 필요합니다.")

    from dartlab.core.messaging import progress

    if sections:
        from dartlab.providers.dart.openapi.client import DartClient
        from dartlab.providers.dart.openapi.zipCollector import _collectOneZip

        progress(f"{company.corpName} 공시 ZIP 다운로드 중... ({rceptNo})")
        client = DartClient()
        parsed = _collectOneZip(client, rceptNo)
        return {
            "docId": rceptNo,
            "market": "KR",
            "title": record.get("title") or record.get("reportNm") or record.get("report_nm") or "",
            "docUrl": viewerUrl or f"{DART_VIEWER}{rceptNo}",
            "viewerUrl": viewerUrl or f"{DART_VIEWER}{rceptNo}",
            "sections": parsed or [],
        }

    from dartlab.providers.dart.openapi.dart import OpenDart

    progress(f"{company.corpName} 공시 원문 다운로드 중... ({rceptNo})")
    rawText = OpenDart().documentText(rceptNo)
    progress(f"{company.corpName} 공시 원문 정리 중... ({rceptNo})")
    normalizedText = _normalizeDocumentText(rawText)
    textPreview, truncated = truncateText(normalizedText, maxChars=maxChars)
    rawPreview, _ = truncateText(rawText, maxChars=maxChars)
    return {
        "docId": rceptNo,
        "market": "KR",
        "title": record.get("title") or record.get("reportNm") or "",
        "docUrl": viewerUrl or f"{DART_VIEWER}{rceptNo}",
        "viewerUrl": viewerUrl or f"{DART_VIEWER}{rceptNo}",
        "raw": rawPreview,
        "text": textPreview,
        "truncated": truncated,
    }


def _normalizeDocumentText(rawText: str) -> str:
    if "<" not in rawText or ">" not in rawText:
        return rawText
    try:
        from dartlab.providers.dart.openapi.collector import _htmlToText

        normalized = _htmlToText(rawText)
    except Exception:
        normalized = ""
    return normalized or rawText
