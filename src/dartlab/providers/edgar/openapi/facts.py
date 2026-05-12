"""EDGAR companyfacts / companyconcept / frames wrapper."""

from __future__ import annotations

from datetime import date
from typing import Any

import polars as pl

from dartlab.providers.edgar.openapi.client import DEFAULT_BASE_URL, EdgarClient

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


def getCompanyFactsJson(cik: str, client: EdgarClient | None = None) -> dict[str, Any]:
    """CIK 로 SEC companyfacts API 를 호출하여 전체 XBRL fact JSON 을 반환.

    Args:
        cik: SEC CIK 번호.
        client: EdgarClient 인스턴스 (None 이면 기본).

    Returns:
        companyfacts API 원본 JSON dict.

    Raises:
        EdgarApiError: API 호출 실패.

    Example:
        >>> getCompanyFactsJson("0000320193")

    SeeAlso:
        - ``EDGAR_COMPANYFACTS_SCHEMA`` — 정규화 schema.
        - ``EdgarClient`` — HTTP backend.

    Requires:
        - dartlab
        - datetime
        - polars

    Capabilities:
        - SEC companyfacts / companyconcept / frames API 위임 + JSON 정규화 → 정규화된 fact schema.

    Guide:
        - "SEC XBRL fact 조회" → 본 모듈 함수.

    AIContext:
        internal facts wrapper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - User-Agent 미설정 → 403.
            - 대량 fact 그대로 LLM 노출 → 토큰 폭증.
        OutputSchema:
            - dict (raw JSON) 또는 pl.DataFrame (EDGAR_COMPANYFACTS_SCHEMA).
        Prerequisites:
            - 인터넷 + SEC EDGAR public API.
        Freshness:
            - SEC EDGAR 실시간.
        Dataflow:
            - CIK/tag/frame → EdgarClient → SEC API → 정규화 → 본 함수.
        TargetMarkets:
            - US (SEC EDGAR XBRL).
    """
    api = client or EdgarClient()
    normalized = str(cik).zfill(10)
    return api.getJson(f"{DEFAULT_BASE_URL}/api/xbrl/companyfacts/CIK{normalized}.json")


def getCompanyConceptJson(
    cik: str,
    taxonomy: str,
    tag: str,
    client: EdgarClient | None = None,
) -> dict[str, Any]:
    """특정 회사의 taxonomy/tag 조합에 대한 concept JSON 을 반환.

    Args:
        cik: SEC CIK 번호.
        taxonomy: XBRL taxonomy (예: ``"us-gaap"``).
        tag: XBRL tag (예: ``"Revenues"``).
        client: EdgarClient 인스턴스.

    Returns:
        concept API 원본 JSON dict.

    Raises:
        EdgarApiError: API 호출 실패.

    Example:
        >>> getCompanyConceptJson("0000320193", "us-gaap", "Revenues")

    SeeAlso:
        - ``EDGAR_COMPANYFACTS_SCHEMA`` — 정규화 schema.
        - ``EdgarClient`` — HTTP backend.

    Requires:
        - dartlab
        - datetime
        - polars

    Capabilities:
        - SEC companyfacts / companyconcept / frames API 위임 + JSON 정규화 → 정규화된 fact schema.

    Guide:
        - "SEC XBRL fact 조회" → 본 모듈 함수.

    AIContext:
        internal facts wrapper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - User-Agent 미설정 → 403.
            - 대량 fact 그대로 LLM 노출 → 토큰 폭증.
        OutputSchema:
            - dict (raw JSON) 또는 pl.DataFrame (EDGAR_COMPANYFACTS_SCHEMA).
        Prerequisites:
            - 인터넷 + SEC EDGAR public API.
        Freshness:
            - SEC EDGAR 실시간.
        Dataflow:
            - CIK/tag/frame → EdgarClient → SEC API → 정규화 → 본 함수.
        TargetMarkets:
            - US (SEC EDGAR XBRL).
    """
    api = client or EdgarClient()
    normalized = str(cik).zfill(10)
    return api.getJson(f"{DEFAULT_BASE_URL}/api/xbrl/companyconcept/CIK{normalized}/{taxonomy}/{tag}.json")


def getFrameJson(
    taxonomy: str,
    tag: str,
    unit: str,
    period: str,
    client: EdgarClient | None = None,
) -> dict[str, Any]:
    """특정 기간의 전체 기업 XBRL frame 데이터를 JSON 으로 반환.

    Args:
        taxonomy: XBRL taxonomy.
        tag: XBRL tag.
        unit: unit (예: ``"USD"``).
        period: 기간 (예: ``"CY2024Q4I"``).
        client: EdgarClient 인스턴스.

    Returns:
        frame API 원본 JSON dict (cross-sectional, 전 기업).

    Raises:
        EdgarApiError: API 호출 실패.

    Example:
        >>> getFrameJson("us-gaap", "Revenues", "USD", "CY2024Q4I")

    SeeAlso:
        - ``EDGAR_COMPANYFACTS_SCHEMA`` — 정규화 schema.
        - ``EdgarClient`` — HTTP backend.

    Requires:
        - dartlab
        - datetime
        - polars

    Capabilities:
        - SEC companyfacts / companyconcept / frames API 위임 + JSON 정규화 → 정규화된 fact schema.

    Guide:
        - "SEC XBRL fact 조회" → 본 모듈 함수.

    AIContext:
        internal facts wrapper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - User-Agent 미설정 → 403.
            - 대량 fact 그대로 LLM 노출 → 토큰 폭증.
        OutputSchema:
            - dict (raw JSON) 또는 pl.DataFrame (EDGAR_COMPANYFACTS_SCHEMA).
        Prerequisites:
            - 인터넷 + SEC EDGAR public API.
        Freshness:
            - SEC EDGAR 실시간.
        Dataflow:
            - CIK/tag/frame → EdgarClient → SEC API → 정규화 → 본 함수.
        TargetMarkets:
            - US (SEC EDGAR XBRL).
    """
    api = client or EdgarClient()
    return api.getJson(f"{DEFAULT_BASE_URL}/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json")


def companyFactsToRows(payload: dict[str, Any]) -> pl.DataFrame:
    """companyfacts JSON 을 flat 한 행 단위 DataFrame 으로 변환.

    Args:
        payload: companyfacts API JSON dict.

    Returns:
        ``EDGAR_COMPANYFACTS_SCHEMA`` 형식 flat DataFrame.

    Raises:
        없음.

    Example:
        >>> companyFactsToRows(getCompanyFactsJson("0000320193"))

    SeeAlso:
        - ``EDGAR_COMPANYFACTS_SCHEMA`` — 정규화 schema.
        - ``EdgarClient`` — HTTP backend.

    Requires:
        - dartlab
        - datetime
        - polars

    Capabilities:
        - SEC companyfacts / companyconcept / frames API 위임 + JSON 정규화 → 정규화된 fact schema.

    Guide:
        - "SEC XBRL fact 조회" → 본 모듈 함수.

    AIContext:
        internal facts wrapper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - User-Agent 미설정 → 403.
            - 대량 fact 그대로 LLM 노출 → 토큰 폭증.
        OutputSchema:
            - dict (raw JSON) 또는 pl.DataFrame (EDGAR_COMPANYFACTS_SCHEMA).
        Prerequisites:
            - 인터넷 + SEC EDGAR public API.
        Freshness:
            - SEC EDGAR 실시간.
        Dataflow:
            - CIK/tag/frame → EdgarClient → SEC API → 정규화 → 본 함수.
        TargetMarkets:
            - US (SEC EDGAR XBRL).
    """
    rows: list[dict[str, Any]] = []
    cik = str(payload.get("cik") or "").zfill(10)
    entityName = str(payload.get("entityName") or "")
    facts = payload.get("facts", {})
    if not isinstance(facts, dict):
        return pl.DataFrame()

    for namespace, tags in facts.items():
        if not isinstance(tags, dict):
            continue
        for tag, tagInfo in tags.items():
            if not isinstance(tagInfo, dict):
                continue
            label = str(tagInfo.get("label") or tag)
            units = tagInfo.get("units", {})
            if not isinstance(units, dict):
                continue
            for unit, entries in units.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    rows.append(
                        {
                            "cik": cik,
                            "entityName": entityName,
                            "namespace": namespace,
                            "tag": tag,
                            "label": label,
                            "unit": str(unit),
                            "val": _asFloat(entry.get("val")),
                            "fy": _asInt(entry.get("fy")),
                            "fp": _asText(entry.get("fp")),
                            "form": _asText(entry.get("form")),
                            "filed": _asDate(entry.get("filed")),
                            "frame": _asText(entry.get("frame")),
                            "start": _asDate(entry.get("start")),
                            "end": _asDate(entry.get("end")),
                            "accn": _asText(entry.get("accn")),
                        }
                    )

    if not rows:
        return pl.DataFrame(schema=EDGAR_COMPANYFACTS_SCHEMA)
    return pl.DataFrame(rows, schema=EDGAR_COMPANYFACTS_SCHEMA)


def _asText(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _asInt(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _asFloat(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _asDate(value: Any) -> date | None:
    text = _asText(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
