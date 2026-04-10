"""DART API 프록시 — 키 없는 사용자를 위한 서버 측 OpenDART 호출.

서버에 DART_API_KEY를 두고, 사용자는 키 없이 실시간 공시 조회.
Rate limit으로 남용 방지, crtfc_key 필드 제거로 키 노출 방지.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/dart", tags=["dart"])
_log = logging.getLogger(__name__)

_MAX_ROWS = 100


def _get_client():
    """서버 측 DartClient 싱글톤."""
    from dartlab.providers.dart.openapi.client import DartClient

    return DartClient()


def _sanitize(data: dict | list) -> dict | list:
    """응답에서 crtfc_key 필드를 제거."""
    if isinstance(data, dict):
        return {k: _sanitize(v) for k, v in data.items() if k != "crtfc_key"}
    if isinstance(data, list):
        return [_sanitize(item) if isinstance(item, (dict, list)) else item for item in data]
    return data


@router.get("/filings")
def dart_filings(
    corp: str | None = Query(None, description="종목코드 또는 corp_code"),
    start: str | None = Query(None, description="시작일 (YYYYMMDD)"),
    end: str | None = Query(None, description="종료일 (YYYYMMDD)"),
    type: str | None = Query(None, description="공시유형 필터"),
):
    """공시 목록 조회."""
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        dart = Dart()
        df = dart.filings(corp=corp, start=start or "20250101", end=end, type=type)
        rows = df.head(_MAX_ROWS).to_dicts()
        return _sanitize({"count": len(rows), "total": df.height, "rows": rows})
    except (ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{corp}")
def dart_company_info(corp: str):
    """기업 기본 정보."""
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        dart = Dart()
        info = dart.company(corp)
        return _sanitize(info)
    except (ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/finance/{corp}")
def dart_finance(
    corp: str,
    year: int | None = Query(None, description="사업연도"),
    quarter: int | None = Query(None, description="분기 (0=연간, 1~3=분기)"),
):
    """재무제표 조회."""
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        dart = Dart()
        df = dart.finstate(corp, start=year, q=quarter)
        rows = df.head(_MAX_ROWS).to_dicts()
        return _sanitize({"count": len(rows), "total": df.height, "rows": rows})
    except (ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/report/{corp}/{category}")
def dart_report(
    corp: str,
    category: str,
    year: int | None = Query(None, description="사업연도"),
):
    """보고서 API (배당, 직원, 임원 등 56개 카테고리)."""
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        dart = Dart()
        df = dart.report(corp, category, start=year)
        rows = df.head(_MAX_ROWS).to_dicts()
        return _sanitize({"count": len(rows), "total": df.height, "rows": rows})
    except (ValueError, KeyError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
