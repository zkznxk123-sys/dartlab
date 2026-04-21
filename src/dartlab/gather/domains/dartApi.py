"""DART OpenAPI gather 어댑터 -- 임원거래 + 대량보유.

기존 providers/dart/openapi/dart.py의 Dart 클래스를 asyncio.to_thread()로 래핑.
API 키 없으면 None 반환 (graceful degradation).
"""

from __future__ import annotations

import asyncio
import logging

from dartlab.core.polarsUtil import isEmptyDf

from ..types import InsiderTrade, MajorHolder

log = logging.getLogger(__name__)


def _getDart():
    """Dart 인스턴스를 lazy 생성.

    Returns
    -------
    Dart | None
        DART OpenAPI 클라이언트 인스턴스. API 키 미설정 또는 import 실패 시 None.
    """
    try:
        from dartlab.providers.dart.openapi.dart import Dart

        return Dart()
    except (ImportError, ValueError, OSError) as exc:
        log.debug("DART API 사용 불가: %s", exc)
        return None


async def fetchInsiderTrading(stockCode: str) -> list[InsiderTrade]:
    """임원/주요주주 주식 거래 내역 -- DART elestock.json.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).

    Returns
    -------
    list[InsiderTrade]
        거래 내역 목록. 각 항목 필드:

        - date : str — 공시 접수일 (YYYYMMDD)
        - name : str — 보고자 성명
        - position : str — 직위
        - tradeType : str — 변동 구분 (취득/처분)
        - changeShares : int — 변동 주식 수 (주)
        - afterShares : int — 변동 후 보유 주식 수 (주)
        - reason : str — 변동 사유
        - source : str — ``"dart"``

        API 키 미설정이거나 조회 실패 시 빈 리스트.
    """
    dart = _getDart()
    if dart is None:
        return []
    try:
        df = await asyncio.to_thread(dart.executiveShares, stockCode)
        if isEmptyDf(df):
            return []
        result = []
        for row in df.iter_rows(named=True):
            result.append(
                InsiderTrade(
                    date=str(row.get("rcept_dt", "")),
                    name=str(row.get("repror", row.get("nm", ""))),
                    position=str(row.get("ofcps", "")),
                    tradeType=str(row.get("sp_stock_lmp_cnt", "")),
                    changeShares=_safeInt(row.get("sp_stock_lmp_cnt", 0)),
                    afterShares=_safeInt(row.get("sp_stock_lmp_irds_cnt", 0)),
                    reason=str(row.get("ctr_motive", "")),
                    source="dart",
                )
            )
        return result
    except (ValueError, OSError, KeyError, TypeError) as exc:
        log.warning("DART executiveShares 실패 (%s): %s", stockCode, exc)
        return []


async def fetchMajorShareholders(stockCode: str) -> list[MajorHolder]:
    """5% 이상 대량보유 변동 -- DART majorstock.json.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).

    Returns
    -------
    list[MajorHolder]
        대량보유 변동 목록. 각 항목 필드:

        - holderName : str — 보고서명 또는 보유자명
        - shares : int — 보유 주식 수 (주)
        - ratio : float — 보유 비율 (%)
        - changeDate : str — 공시 접수일 (YYYYMMDD)
        - changeType : str — 변동 구분
        - source : str — ``"dart"``

        API 키 미설정이거나 조회 실패 시 빈 리스트.
    """
    dart = _getDart()
    if dart is None:
        return []
    try:
        df = await asyncio.to_thread(dart.majorShareholders, stockCode)
        if isEmptyDf(df):
            return []
        result = []
        for row in df.iter_rows(named=True):
            result.append(
                MajorHolder(
                    holderName=str(row.get("report_nm", row.get("nm", ""))),
                    shares=_safeInt(row.get("stkqy", 0)),
                    ratio=_safeFloat(row.get("stkrt", 0)),
                    changeDate=str(row.get("rcept_dt", "")),
                    changeType=str(row.get("change_on", "")),
                    source="dart",
                )
            )
        return result
    except (ValueError, OSError, KeyError, TypeError) as exc:
        log.warning("DART majorShareholders 실패 (%s): %s", stockCode, exc)
        return []


def _safeInt(val) -> int:
    """안전한 int 변환 — 콤마, +기호 제거 포함.

    Parameters
    ----------
    val
        변환할 값. str, int, float 또는 None.

    Returns
    -------
    int
        변환된 정수. None이거나 변환 불가 시 0.
    """
    if val is None:
        return 0
    try:
        return int(str(val).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, TypeError):
        return 0


def _safeFloat(val) -> float:
    """안전한 float 변환 — 콤마, +기호 제거 포함.

    Parameters
    ----------
    val
        변환할 값. str, int, float 또는 None.

    Returns
    -------
    float
        변환된 실수. None이거나 변환 불가 시 0.0.
    """
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, TypeError):
        return 0.0
