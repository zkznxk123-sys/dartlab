from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sse_starlette.sse import EventSourceResponse

import dartlab
from dartlab.core.polarsUtil import isEmptyDf

_PERIOD_COL_RE = re.compile(r"^\d{4}(Q[1-4])?$")

from ..services.aiAnalysis import streamTopicSummary
from ..services.companyApi import (
    buildDiffSummary,
    buildToc,
    buildViewer,
    filterBlocksByPeriod,
    getCompany,
    safeTopicLabel,
)
from .common import (
    HANDLED_API_ERRORS,
    etagResponse,
    guideDetail,
    normalizeProviderName,
    serializePayload,
)

router = APIRouter()


@router.get("/api/search")
def apiSearch(q: str = Query(..., min_length=1)):
    """종목 검색 — substring 우선, 결과 없으면 fuzzy(초성/Levenshtein) fallback."""
    try:
        df = dartlab.searchName(q)
        rows = df.to_dicts() if len(df) > 0 else []
        fuzzy_used = False

        if not rows:
            from dartlab.gather.listing import fuzzySearch

            df = fuzzySearch(q, maxResults=20)
            rows = df.to_dicts() if len(df) > 0 else []
            fuzzy_used = bool(rows)

        mapped = []
        for row in rows[:20]:
            mapped.append(
                {
                    "corpName": row.get("회사명", row.get("corpName", "")),
                    "stockCode": row.get("종목코드", row.get("stockCode", "")),
                    "market": row.get("시장구분", ""),
                    "sector": row.get("업종", ""),
                }
            )
        return {"results": mapped, "fuzzy": fuzzy_used}
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=400, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}")
def apiCompany(code: str):
    """종목 기본 정보 + 사용 가능 API surface 목록."""
    try:
        company = getCompany(code)
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "surface": {
                "index": f"/api/company/{company.stockCode}/index",
                "show": f"/api/company/{company.stockCode}/show/{{topic}}",
                "trace": f"/api/company/{company.stockCode}/trace/{{topic}}",
            },
            "profile": {
                "status": "roadmap",
                "description": "변화 지점을 문서처럼 읽는 company report view가 추후 추가될 예정입니다.",
            },
        }
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/index")
def apiCompanyIndex(code: str, request: Request, response: Response):
    """회사 데이터 구조 인덱스 DataFrame."""
    try:
        company = getCompany(code)
        data = {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "payload": serializePayload(company.index),
        }
        return etagResponse(request, response, data, maxAge=300, swr=1800)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/sections")
def apiCompanySections(code: str, request: Request, response: Response):
    """merged topic x period 수평화 테이블."""
    try:
        company = getCompany(code)
        data = {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "payload": serializePayload(company.sections, maxRows=5000),
        }
        return etagResponse(request, response, data, maxAge=300, swr=1800)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/init")
def apiCompanyInit(code: str, request: Request, response: Response):
    """SPA 초기 로드용 번들 — toc + 첫 topic viewer + diff 요약."""
    try:
        company = getCompany(code)
        toc_data = buildToc(company)

        first_topic: str | None = None
        first_chapter: str | None = None
        chapters = toc_data.get("chapters", [])
        if chapters:
            topics = chapters[0].get("topics", [])
            if topics:
                first_topic = topics[0]["topic"]
                first_chapter = chapters[0]["chapter"]

        viewer_data = None
        diff_data = None
        if first_topic:
            viewer_data = buildViewer(company, first_topic)
            diff_data = buildDiffSummary(company, first_topic)

        result = {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "toc": toc_data,
            "firstTopic": first_topic,
            "firstChapter": first_chapter,
            "viewer": viewer_data,
            "diffSummary": diff_data,
        }
        return etagResponse(request, response, result, maxAge=300, swr=1800)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/toc")
def apiCompanyToc(code: str, request: Request, response: Response):
    """목차(TOC) — chapter/topic 트리 구조."""
    try:
        company = getCompany(code)
        data = buildToc(company)
        return etagResponse(request, response, data, maxAge=300, swr=1800)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/viewer/{topic}")
def apiCompanyViewerTopic(
    code: str,
    topic: str,
    request: Request,
    period: str | None = Query(None, description="특정 기간만 반환 (타임라인 클릭 최적화)"),
    response: Response = None,
):
    """단일 topic의 viewer 데이터 — sections 블록 + 텍스트 문서."""
    try:
        company = getCompany(code)

        if period is not None:
            from dartlab.providers.dart.docs.viewer import (
                serializeViewerBlock,
                serializeViewerTextDocument,
                viewerBlocks,
                viewerTextDocument,
            )

            if not hasattr(company, "_viewer_cache"):
                company._viewer_cache = {}
            if topic in company._viewer_cache:
                blocks = company._viewer_cache[topic]
            else:
                blocks = viewerBlocks(company, topic)
                company._viewer_cache[topic] = blocks
            blocks = filterBlocksByPeriod(blocks, period)
            data = {
                "stockCode": company.stockCode,
                "corpName": company.corpName,
                "topic": topic,
                "topicLabel": safeTopicLabel(company, topic),
                "period": period,
                "blocks": [serializeViewerBlock(block) for block in blocks],
                "textDocument": serializeViewerTextDocument(viewerTextDocument(topic, blocks)),
            }
        else:
            data = buildViewer(company, topic)

        return etagResponse(request, response, data, maxAge=120, swr=600)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/viewer2/{topic}")
def apiViewerDoc(
    code: str,
    topic: str,
    request: Request,
    base: str | None = Query(None),
    compare: str | None = Query(None),
    response: Response = None,
):
    """sections 기반 신구대조 뷰어 — viewer() dict 반환."""
    try:
        company = getCompany(code)
        sec = company._docs.sections.raw
        if sec is None:
            raise HTTPException(status_code=404, detail="sections 없음")

        if not base:
            periods = sorted(
                [c for c in sec.columns if _PERIOD_COL_RE.fullmatch(c)],
                reverse=True,
            )
            base = periods[0] if periods else None

        from dartlab.core.docs.viewer import viewer

        doc = viewer(sec, topic, base, compare)
        doc["stockCode"] = company.stockCode
        doc["corpName"] = company.corpName
        doc["topicLabel"] = safeTopicLabel(company, topic)
        return etagResponse(request, response, doc, maxAge=120, swr=600)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.post("/api/company/{code}/viewer/batch")
async def apiCompanyViewerBatch(code: str, request: Request, response: Response):
    """여러 topic의 viewer 데이터를 한 번에 반환 — chapter 확장 시 N+1 제거."""
    body = await request.json()
    topics = body.get("topics", [])
    if not topics or not isinstance(topics, list):
        raise HTTPException(status_code=400, detail="topics 배열 필요")
    topics = topics[:20]  # 최대 20개 제한

    try:
        company = getCompany(code)
        results = {}
        for topic in topics:
            if not isinstance(topic, str):
                continue
            try:
                results[topic] = buildViewer(company, topic)
            except HANDLED_API_ERRORS:
                results[topic] = None
        return etagResponse(request, response, {"results": results}, maxAge=120, swr=600)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/show/{topic}/all")
def apiCompanyShowAll(code: str, topic: str, raw: bool = Query(False)):
    """topic의 전 기간 viewer 블록 일괄 반환."""
    try:
        from dartlab.providers.dart.docs.viewer import (
            serializeViewerBlock,
            serializeViewerTextDocument,
            viewerBlocks,
            viewerTextDocument,
        )

        company = getCompany(code)
        blocks = viewerBlocks(company, topic)
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "topic": topic,
            "blocks": [serializeViewerBlock(block) for block in blocks],
            "textDocument": serializeViewerTextDocument(viewerTextDocument(topic, blocks)),
        }
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.post("/api/company/{code}/show/{topic}/{block_idx}/parse")
async def apiParseRawTable(code: str, topic: str, blockIdx: int):
    """원문 테이블 블록을 구조화 DataFrame으로 파싱."""
    try:
        from dartlab.providers.dart.docs.tableAI import parseRawMarkdownBlock
        from dartlab.providers.dart.docs.viewer import viewerBlocks

        company = getCompany(code)
        blocks = viewerBlocks(company, topic)
        target = None
        for block in blocks:
            if block.block == blockIdx and block.kind == "raw_markdown":
                target = block
                break
        if target is None:
            raise HTTPException(status_code=404, detail="raw_markdown 블록이 아님")

        result = await parseRawMarkdownBlock(target.rawMarkdown, topic)
        return {
            "stockCode": company.stockCode,
            "topic": topic,
            "block": blockIdx,
            "parsed": result,
        }
    except HTTPException:
        raise
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=500, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/show/{topic}")
def apiCompanyShow(code: str, topic: str, block: int | None = Query(None), raw: bool = Query(False)):
    """topic payload 조회 — show(topic) API 대응."""
    try:
        company = getCompany(code)
        if block is not None:
            result = company.show(topic, block, period=None, raw=raw)
        else:
            result = company.show(topic)
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "topic": topic,
            "block": block,
            "payload": serializePayload(result),
        }
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/trace/{topic}")
def apiCompanyTrace(code: str, topic: str):
    """source provenance 조회 — trace(topic) API 대응."""
    try:
        company = getCompany(code)
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "topic": topic,
            "payload": serializePayload(company.trace(topic)),
        }
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc


@router.get("/api/company/{code}/summary/{topic}")
async def apiCompanyTopicSummary(
    code: str,
    topic: str,
    provider: str | None = None,
    model: str | None = None,
):
    """topic 데이터를 LLM으로 요약하여 SSE 스트리밍 반환."""
    try:
        company = getCompany(code)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc

    try:
        overview = company.show(topic)
    except (AttributeError, KeyError, TypeError, ValueError):
        overview = None
    if overview is None:
        raise HTTPException(status_code=404, detail=f"topic '{topic}' 데이터 없음")

    return EventSourceResponse(
        streamTopicSummary(
            company,
            topic,
            provider=normalizeProviderName(provider) or provider,
            model=model,
        )
    )


@router.get("/api/company/{code}/insights")
def apiCompanyInsights(code: str):
    """7영역 인사이트 등급 (A~F) + 이상 징후."""
    try:
        company = getCompany(code)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc

    from dartlab.analysis.financial.insight.pipeline import analyzeFinancial as insight_analyze

    try:
        result = insight_analyze(company.stockCode, company=company)
    except HANDLED_API_ERRORS:
        result = None

    if result is None:
        return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}

    def _flagDict(flag):
        return {"level": flag.level, "category": flag.category, "text": flag.text}

    def _insightDict(insight):
        return {
            "grade": insight.grade,
            "summary": insight.summary,
            "details": insight.details,
            "risks": [_flagDict(risk) for risk in insight.risks],
            "opportunities": [_flagDict(opportunity) for opportunity in insight.opportunities],
        }

    def _anomalyDict(anomaly):
        return {
            "severity": anomaly.severity,
            "category": anomaly.category,
            "text": anomaly.text,
            "value": anomaly.value,
        }

    return {
        "stockCode": company.stockCode,
        "corpName": company.corpName,
        "available": True,
        "isFinancial": result.isFinancial,
        "grades": result.grades(),
        "areas": {
            "performance": _insightDict(result.performance),
            "profitability": _insightDict(result.profitability),
            "health": _insightDict(result.health),
            "cashflow": _insightDict(result.cashflow),
            "governance": _insightDict(result.governance),
            "risk": _insightDict(result.risk),
            "opportunity": _insightDict(result.opportunity),
        },
        "anomalies": [_anomalyDict(anomaly) for anomaly in result.anomalies],
        "summary": result.summary,
        "profile": result.profile,
    }


@router.get("/api/company/{code}/network")
def apiCompanyNetwork(code: str, hops: int = 1):
    """관계사 네트워크 그래프 — ego 중심 N-hop."""
    hops = max(1, min(hops, 3))
    try:
        company = getCompany(code)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc

    try:
        result = company._ensureNetwork()
        if result is None:
            return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}
        data, full = result

        from dartlab.scan.network.export import exportEgo

        ego = exportEgo(data, full, company.stockCode, hops=hops)
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "available": True,
            **ego,
        }
    except HANDLED_API_ERRORS:
        return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}


@router.get("/api/company/{code}/scan/{axis}")
def apiCompanyScan(code: str, axis: str):
    """6-Axis 스캔 단일 축 결과 + 시장 내 위치."""
    try:
        company = getCompany(code)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc

    valid_axes = {"governance", "workforce", "capital", "debt"}

    if axis == "all":
        results = {}
        for current_axis in valid_axes:
            method = getattr(company, current_axis, None)
            if method is None:
                continue
            try:
                df = method()
                if df is not None and not df.is_empty():
                    results[current_axis] = serializePayload(df)
            except HANDLED_API_ERRORS:
                continue
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "available": bool(results),
            "scans": results,
        }

    if axis not in valid_axes:
        raise HTTPException(status_code=400, detail=f"유효한 축: {', '.join(sorted(valid_axes))}, all")

    method = getattr(company, axis, None)
    if method is None:
        return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}

    try:
        df = method()
        if isEmptyDf(df):
            return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "available": True,
            "scanType": axis,
            "payload": serializePayload(df),
        }
    except HANDLED_API_ERRORS:
        return {"stockCode": company.stockCode, "corpName": company.corpName, "available": False}


@router.get("/api/company/{code}/scan/position")
def apiCompanyScanPosition(code: str):
    """6-Axis 전체 포지션 요약 — 사전 빌드 스냅샷 기반."""
    from dartlab.scan.snapshot import getScanPosition

    position = getScanPosition(code)
    if position is None:
        raise HTTPException(status_code=404, detail="scan 스냅샷 없음 — buildScanSnapshot() 선행 필요")

    return {
        "stockCode": code,
        "available": True,
        "position": position,
    }


@router.get("/api/company/{code}/insights/unified")
def apiCompanyInsightsUnified(code: str):
    """통합 인사이트 — 등급 + 스캔 + 피어 결합."""
    try:
        company = getCompany(code)
    except HANDLED_API_ERRORS as exc:
        raise HTTPException(status_code=404, detail=guideDetail(exc)) from exc

    from dartlab.scan.payload import buildUnifiedPayload

    try:
        unified = buildUnifiedPayload(company)
    except HANDLED_API_ERRORS:
        unified = {}

    return {
        "stockCode": company.stockCode,
        "corpName": company.corpName,
        "available": bool(unified),
        "areas": unified,
    }
