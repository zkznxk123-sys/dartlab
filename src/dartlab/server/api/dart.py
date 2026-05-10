"""DART 데이터 API — HuggingFace 사전빌드 데이터 기반 즉시 응답.

재무제표, 보고서, 공시 목록 등 대부분의 데이터는 이미 HuggingFace에 있다.
OpenDART API를 실시간 호출하지 않고, dartlab Company/listing으로 HF 데이터를 반환.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/dart", tags=["dart"])
_log = logging.getLogger(__name__)

_MAX_ROWS = 200


def _dfToResponse(df, maxRows: int = _MAX_ROWS) -> dict:
    """DataFrame → JSON 응답."""
    if df is None or (hasattr(df, "is_empty") and df.is_empty()):
        return {"count": 0, "total": 0, "rows": []}
    total = df.height if hasattr(df, "height") else len(df)
    rows = df.head(maxRows).to_dicts() if hasattr(df, "to_dicts") else []
    return {"count": len(rows), "total": total, "rows": rows}


@router.get("/filings")
def dartFilings(
    corp: str | None = Query(None, description="종목코드"),
    topK: int = Query(20, description="최대 건수"),
):
    """공시 목록 — HF 데이터 기반."""
    try:
        import dartlab

        if corp:
            c = dartlab.Company(corp)
            df = c.filings(topK=topK)
        else:
            df = dartlab.listing("filings")
        return _dfToResponse(df, maxRows=topK)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{corp}")
def dartCompanyInfo(corp: str):
    """기업 기본 정보 — HF 데이터 기반."""
    try:
        import dartlab

        c = dartlab.Company(corp)
        return {
            "corpName": c.corpName,
            "stockCode": c.stockCode,
            "market": getattr(c, "market", None),
            "currency": getattr(c, "currency", None),
        }
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/finance/{corp}")
def dartFinance(
    corp: str,
    statement: str = Query("IS", description="IS/BS/CF/CIS/SCE"),
    freq: str = Query("Q", description="Q(분기)/Y(연간)"),
):
    """재무제표 — HF parquet 즉시 반환."""
    try:
        import dartlab

        c = dartlab.Company(corp)
        if freq == "Y":
            df = c.show(statement, freq="Y")
        else:
            df = c.show(statement)
        return _dfToResponse(df)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/show/{corp}/{topic}")
def dartShow(
    corp: str,
    topic: str,
    period: str | None = Query(None, description="기간 필터"),
):
    """공시 토픽 데이터 — HF parquet 즉시 반환."""
    try:
        import dartlab

        c = dartlab.Company(corp)
        if period:
            result = c.show(topic, period=period)
        else:
            result = c.show(topic)
        if hasattr(result, "to_dicts"):
            return _dfToResponse(result)
        return {"data": str(result)[:5000]}
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/report/{corp}/{category}")
def dartReport(
    corp: str,
    category: str,
):
    """보고서 (배당, 직원, 임원 등) — HF parquet 즉시 반환."""
    try:
        import dartlab

        c = dartlab.Company(corp)
        df = c.show(category)
        if hasattr(df, "to_dicts"):
            return _dfToResponse(df)
        return {"data": str(df)[:5000]}
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scan/{axis}")
def dartScan(
    axis: str,
    target: str | None = Query(None, description="축별 대상 (account: 계정명, ratio: 비율명)"),
):
    """전종목 횡단분석 — 프리빌드 parquet 즉시 반환."""
    try:
        import dartlab

        if target:
            df = dartlab.scan(axis, target)
        else:
            df = dartlab.scan(axis)
        return _dfToResponse(df)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/search")
def dartSearch(
    q: str = Query(..., description="검색어"),
    corp: str | None = Query(None, description="종목코드 필터"),
):
    """공시 원문 검색 — stemIndex 즉시 반환."""
    try:
        import dartlab

        if corp:
            df = dartlab.search(q, corp=corp)
        else:
            df = dartlab.search(q)
        return _dfToResponse(df)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/listing")
def dartListing(
    kind: str = Query("companies", description="companies/filings/topics"),
    corp: str | None = Query(None, description="filings 시 종목코드"),
):
    """상장 종목/공시 목록."""
    try:
        import dartlab

        if kind == "filings" and corp:
            df = dartlab.listing("filings", corp=corp)
        else:
            df = dartlab.listing(kind)
        return _dfToResponse(df)
    except (ValueError, KeyError, RuntimeError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
