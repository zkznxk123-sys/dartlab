"""DART OpenAPI 임원거래 + 대량보유 — gather/types 변환.

이전 위치: gather/domains/dartApi.py (gather → providers cycle 의 한 축).
새 위치: providers/dart 안 — DART OpenAPI 호출 자체는 provider 책임. gather 는
provider 의 결과를 gather.types schema 로 받아쓸 뿐 (gather → providers 단방향).

이 파일은 providers/dart 내부에서 DART OpenAPI Dart 클라이언트 사용 + gather.types
schema (InsiderTrade/MajorHolder) 로 변환. gather/domains/dartApi.py 의 본체.
"""

from __future__ import annotations

import asyncio
import logging

from dartlab.core.polarsUtil import isEmptyDf

log = logging.getLogger(__name__)


# 자체 raw dataclass — providers/dart 가 gather.types 의존 없이 dict 반환.
# gather/insider.py 가 dict → gather.types.InsiderTrade/MajorHolder 변환 책임.
# (cycle 회피: providers → gather 의존 0, gather → providers 단방향만.)


def _getDart():
    """Dart OpenAPI 클라이언트 lazy 생성. API 키 미설정 시 None."""
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        return Dart()
    except (ImportError, ValueError, OSError) as exc:
        log.debug("DART API 사용 불가: %s", exc)
        return None


async def fetchInsiderTradingRaw(stockCode: str, *, limit: int | None = None) -> list[dict]:
    """임원/주요주주 주식 거래 내역 raw dict — DART elestock.json.

    Args:
        stockCode: 종목코드.
        limit: 최대 행 수. None 이면 무제한.

    Returns:
        각 거래의 표준화된 dict 리스트 (date/name/position/tradeType/changeShares/afterShares/reason/source).
        호출자 (gather/insider.py) 가 ``InsiderTrade`` dataclass 로 변환.

    Example:
        >>> await fetchInsiderTradingRaw("005930", limit=20)

    Raises:
        없음.
    """
    dart = _getDart()
    if dart is None:
        return []
    try:
        df = await asyncio.to_thread(dart.executiveShares, stockCode)
        if isEmptyDf(df):
            return []
        result: list[dict] = []
        for row in df.iter_rows(named=True):
            result.append(
                {
                    "date": str(row.get("rcept_dt", "")),
                    "name": str(row.get("repror", row.get("nm", ""))),
                    "position": str(row.get("ofcps", "")),
                    "tradeType": str(row.get("sp_stock_lmp_cnt", "")),
                    "changeShares": _safeInt(row.get("sp_stock_lmp_cnt", 0)),
                    "afterShares": _safeInt(row.get("sp_stock_lmp_irds_cnt", 0)),
                    "reason": str(row.get("ctr_motive", "")),
                    "source": "dart",
                }
            )
        if limit is not None:
            result = result[:limit]
        return result
    except (ValueError, OSError, KeyError, TypeError) as exc:
        log.warning("DART executiveShares 실패 (%s): %s", stockCode, exc)
        return []


async def fetchMajorShareholdersRaw(stockCode: str, *, limit: int | None = None) -> list[dict]:
    """5% 이상 대량보유 변동 raw dict — DART majorstock.json.

    Args:
        stockCode: 종목코드.
        limit: 최대 행 수. None 이면 무제한.

    Returns:
        holderName/shares/ratio/changeDate/changeType/source dict 리스트.
        호출자가 ``MajorHolder`` dataclass 변환.

    Example:
        >>> await fetchMajorShareholdersRaw("005930", limit=10)

    Raises:
        없음.
    """
    dart = _getDart()
    if dart is None:
        return []
    try:
        df = await asyncio.to_thread(dart.majorShareholders, stockCode)
        if isEmptyDf(df):
            return []
        result: list[dict] = []
        for row in df.iter_rows(named=True):
            result.append(
                {
                    "holderName": str(row.get("report_nm", row.get("nm", ""))),
                    "shares": _safeInt(row.get("stkqy", 0)),
                    "ratio": _safeFloat(row.get("stkrt", 0)),
                    "changeDate": str(row.get("rcept_dt", "")),
                    "changeType": str(row.get("change_on", "")),
                    "source": "dart",
                }
            )
        if limit is not None:
            result = result[:limit]
        return result
    except (ValueError, OSError, KeyError, TypeError) as exc:
        log.warning("DART majorShareholders 실패 (%s): %s", stockCode, exc)
        return []


async def iterInsiderTradingRaw(stockCode: str, *, limit: int | None = None):
    """``fetchInsiderTradingRaw`` 의 async iterator pair (룰 10).

    Args:
        stockCode: 종목코드.
        limit: 최대 행 수. None 이면 무제한.

    Yields:
        거래 dict.

    Raises:
        없음 (DART 키 부재 또는 API 실패 시 빈 generator).

    Example:
        >>> async for row in iterInsiderTradingRaw("005930", limit=10):
        ...     print(row["name"])
    """
    rows = await fetchInsiderTradingRaw(stockCode, limit=limit)
    for r in rows:
        yield r


async def iterMajorShareholdersRaw(stockCode: str, *, limit: int | None = None):
    """``fetchMajorShareholdersRaw`` 의 async iterator pair (룰 10).

    Args:
        stockCode: 종목코드.
        limit: 최대 행 수. None 이면 무제한.

    Yields:
        대량보유 변동 dict.

    Raises:
        없음 (DART 키 부재 또는 API 실패 시 빈 generator).

    Example:
        >>> async for row in iterMajorShareholdersRaw("005930", limit=10):
        ...     print(row["holderName"])
    """
    rows = await fetchMajorShareholdersRaw(stockCode, limit=limit)
    for r in rows:
        yield r


def _safeInt(val) -> int:
    """안전한 int 변환 — 콤마/기호 제거. None/실패 시 0."""
    if val is None:
        return 0
    try:
        return int(str(val).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, TypeError):
        return 0


def _safeFloat(val) -> float:
    """안전한 float 변환 — 콤마/기호 제거. None/실패 시 0.0."""
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, TypeError):
        return 0.0
