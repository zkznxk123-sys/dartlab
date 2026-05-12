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
    """CIK → SEC companyfacts API 호출 → 전체 XBRL fact JSON 반환 — EDGAR XBRL 본진.

    SEC ``data.sec.gov/api/xbrl/companyfacts/CIK{CIK_10_padded}.json`` endpoint 호출.
    응답은 회사의 **전체 us-gaap concept × 분기 fact** 매트릭스 — 한 회사당 수 MB~수십 MB
    JSON. 100+ concept × 10+ 년 × 4 분기 = ~수만 fact.

    응답 구조:
      - ``cik`` / ``entityName`` (str).
      - ``facts``: ``{taxonomy: {tag: {label, description, units: {unit: [fact dict]}}}}``.
      - 각 fact dict: ``{end, val, accn, fy, fp, form, filed, frame, ...}``.
      - taxonomy: ``"us-gaap"`` (표준) / ``"dei"`` (entity 메타) / ``"ifrs-full"`` (외국 발행자).
      - unit: ``"USD"`` / ``"USD/shares"`` / ``"shares"`` / ``"pure"`` / ``"USD/CFB"`` 등.

    Args:
        cik: SEC CIK (zero-padded 10 권장, 짧으면 자동 ``zfill(10)``).
            예: ``"0000320193"`` (Apple) / ``"320193"`` (동치).
        client: ``EdgarClient`` 인스턴스. None 이면 default (User-Agent header 자동).

    Returns:
        dict — SEC companyfacts JSON 원본 (가공 X).
        ``companyFactsToRows`` 로 정규화 → ``EDGAR_COMPANYFACTS_SCHEMA`` 따르는 pl.DataFrame.

    Raises:
        EdgarApiError: HTTP 호출 실패 (403 User-Agent / 404 CIK 미등록 / 429 rate limit).

    Example:
        >>> json = getCompanyFactsJson("0000320193")  # Apple
        >>> revenues = json["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
        >>> len(revenues)  # 분기 × 연 fact 수

    SeeAlso:
        - ``companyFactsToRows`` — 본 함수 결과 → pl.DataFrame 정규화.
        - ``getCompanyConceptJson`` — 단일 (taxonomy, tag) 조합 조회 (가벼움).
        - ``getFrameJson`` — 횡단 발굴 (단일 concept × 분기 × 전종목).
        - ``EDGAR_COMPANYFACTS_SCHEMA`` — 정규화 schema 정의.
        - ``EdgarClient`` — HTTP backend (User-Agent / retry / rate limit).
        - ``providers.edgar.finance.xbrlConcepts.normalizeConcept`` — concept 정규화 후속.

    Requires:
        - dartlab.providers.edgar.openapi.client (``EdgarClient``)
        - datetime / polars (downstream 정규화)
        - SEC EDGAR public API 접근 (User-Agent header 필수).

    Capabilities:
        - 회사 전체 XBRL fact bulk fetch — 분석/scan/concept 매핑 backend.
        - ``companyfactsBulk`` 가 본 함수 multi-CIK 병렬 호출로 universe 구축.
        - JSON 원본 반환 — caller 가 schema 정규화 또는 raw 분석 선택.

    Guide:
        - 단일 종목 deep dive → 본 함수 + ``companyFactsToRows``.
        - 단일 concept 만 필요 시 ``getCompanyConceptJson`` (더 가벼움).
        - 횡단 발굴 시 ``getFrameJson`` (분기 × 전종목, 본 함수보다 효율적).
        - 본 함수 + caller-side cache → SEC rate limit 회피 (10 req/sec).

    AIContext:
        Ask Workbench EDGAR XBRL core — LLM 이 US 회사 재무 fact retrieval 시 entry.
        결과 → ``scanAccount`` / ``c.show("IS")`` 등 backend 매핑.

    LLM Specifications:
        AntiPatterns:
            - SEC User-Agent header 미설정 → HTTP 403. ``DARTLAB_USER_AGENT`` 환경변수 설정.
            - 본 함수 N 회 짧은 간격 호출 → 10 req/sec rate limit → 429. EdgarClient 가 back-off.
            - 대량 fact JSON 그대로 LLM context 주입 X — 토큰 폭증. ``companyFactsToRows`` 후 필터 의무.
            - CIK 미등록 호출 → 404. ``identity.resolveIssuer`` 사전 검증.
            - JSON 원본을 그대로 분석 X — schema 정규화 (``companyFactsToRows``) 후 polars 처리.
            - 외국 발행자 (``ifrs-full`` taxonomy) 처리 시 us-gaap 가정 X — taxonomy 명시 분기.
        OutputSchema:
            - dict — ``{"cik": str, "entityName": str, "facts": {taxonomy: {tag: ...}}}``.
            - ``facts.<taxonomy>.<tag>.units.<unit>`` = list of fact dict
              (``end`` / ``val`` / ``accn`` / ``fy`` / ``fp`` / ``form`` / ``filed`` / ``frame``).
            - ``companyFactsToRows`` 변환 시 pl.DataFrame — ``cik`` / ``taxonomy`` / ``tag``
              / ``unit`` / ``end`` (Date) / ``val`` (Float) / ``accn`` / ``fy`` / ``fp`` / ``form``.
        Prerequisites:
            - 인터넷 + SEC EDGAR public API 접근 권한.
            - User-Agent header (SEC 정책 — "name email" 형식 권장).
            - ``EdgarClient`` retry / rate limit / cache backend.
        Freshness:
            - SEC EDGAR XBRL 실시간 갱신 — 10-K / 10-Q 제출 후 즉시 반영.
            - 분기 마감 → 10-Q 제출 ~45 일 / 연 마감 → 10-K ~60-90 일 cadence.
            - companyfacts JSON 은 회사가 새 fact 제출 시 즉시 변경.
        Dataflow:
            - CIK (raw) → ``.zfill(10)`` 정규화
            - → ``EdgarClient.getJson`` (HTTP GET + User-Agent + retry + rate limit)
            - → SEC API ``data.sec.gov/api/xbrl/companyfacts/CIK{padded}.json``
            - → JSON dict (raw, 가공 X) → caller.
        TargetMarkets:
            - US (SEC EDGAR XBRL) — NYSE/NASDAQ/AMEX/OTC SEC 등록 + XBRL 제출 종목.
            - 외국 발행자 (``ifrs-full`` taxonomy) 도 지원하나 본 함수는 taxonomy 무관 raw.
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
