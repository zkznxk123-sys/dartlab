"""네이버 글로벌 주식 — US/글로벌 주가 (Yahoo 대체).

네이버 웹 스크래핑. 공식 API 아님.
Reuters Code 체계: NASDAQ → .O, NYSE → 접미사 없음.
**호출 간 3~6초 강제 딜레이** — 서버 보호.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone

from ..types import PriceSnapshot, SourceUnavailableError

log = logging.getLogger(__name__)

_API_BASE = "https://api.stock.naver.com"

# Reuters Code 접미사 후보 (순서대로 시도)
_SUFFIXES = ["", ".O", ".N", ".K", ".A"]

# 서버 보호: 호출 간 3~6초 강제 딜레이 (모듈 전역)
_MIN_DELAY = 0.5
_MAX_DELAY = 1.5
_last_call_time: float = 0.0


async def _throttle() -> None:
    """마지막 호출 이후 3~6초 대기. 별도 호출이어도 무조건."""
    global _last_call_time
    now = time.monotonic()
    elapsed = now - _last_call_time
    delay = random.uniform(_MIN_DELAY, _MAX_DELAY)
    if elapsed < delay:
        wait = delay - elapsed
        await asyncio.sleep(wait)
    _last_call_time = time.monotonic()


def _clean_number(val) -> float | None:
    """문자열/숫자 → float. 실패 시 None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


async def _resolve_reuters_code(ticker: str, client) -> str | None:
    """ticker → 네이버 Reuters Code. 접미사를 순서대로 시도."""
    for suffix in _SUFFIXES:
        await _throttle()
        code = f"{ticker}{suffix}"
        url = f"{_API_BASE}/stock/{code}/basic"
        try:
            resp = await client.get(url, headers={"Accept": "application/json"})
            data = resp.json()
            if data.get("stockName") and not data.get("code", "").startswith("Stock"):
                return code
        except (SourceUnavailableError, ValueError, KeyError):
            continue
    return None


async def fetch_price(stock_code: str, client, *, market: str = "US") -> PriceSnapshot | None:
    """네이버 글로벌 → 현재가 스냅샷."""
    code = await _resolve_reuters_code(stock_code, client)
    if not code:
        log.warning("naver_global: %s 매핑 실패", stock_code)
        return None

    await _throttle()
    url = f"{_API_BASE}/stock/{code}/basic"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver_global price 실패 (%s): %s", stock_code, exc)
        return None

    current = _clean_number(data.get("closePrice"))
    if not current:
        return None

    change = _clean_number(data.get("compareToPreviousClosePrice")) or 0.0
    change_pct = _clean_number(data.get("fluctuationsRatio")) or 0.0
    volume = int(_clean_number(data.get("accumulatedTradingVolume")) or 0)

    # 시가총액 (억 달러 → 달러)
    market_cap = 0.0
    market_cap_raw = data.get("marketValue")
    if market_cap_raw:
        mc = _clean_number(market_cap_raw)
        if mc:
            market_cap = mc  # 네이버 API가 원단위로 줄 수 있음

    # 52주 고저, PER 등은 별도 API 필요 — 기본값
    exchange_name = ""
    ex_type = data.get("stockExchangeType", {})
    if isinstance(ex_type, dict):
        exchange_name = ex_type.get("name", "")

    return PriceSnapshot(
        current=current,
        change=change,
        change_pct=change_pct,
        high_52w=0.0,
        low_52w=0.0,
        volume=volume,
        market_cap=market_cap,
        per=None,
        pbr=None,
        dividend_yield=None,
        source="naver_global",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        currency="USD",
        exchange=exchange_name,
        market=market,
    )


async def fetch_history(
    stock_code: str,
    client,
    *,
    start: str = "",
    end: str = "",
    market: str = "US",
    **kwargs,
) -> list[dict]:
    """네이버 글로벌 → OHLCV 히스토리.

    네이버 글로벌 chart API는 periodType별 110개 하드 제한.
    → 요청 기간에 따라 자동 선택:
      - 1년 이내: dayCandle (약 110 거래일 = 6개월)
      - 1~2년: weekCandle (약 110주 = 2년)
      - 2년 이상: monthCandle (약 110개월 = 9년)
    start 미지정이면 dayCandle (하위호환).
    """
    code = await _resolve_reuters_code(stock_code, client)
    if not code:
        return []

    # 요청 기간 길이로 periodType 자동 선택
    period_type = "dayCandle"
    if start:
        try:
            from datetime import date
            from datetime import datetime as _dt

            start_dt = _dt.strptime(start, "%Y-%m-%d").date()
            end_dt = _dt.strptime(end, "%Y-%m-%d").date() if end else date.today()
            span_days = (end_dt - start_dt).days
            if span_days > 730:
                period_type = "monthCandle"
            elif span_days > 365:
                period_type = "weekCandle"
        except (ValueError, TypeError):
            pass

    await _throttle()
    count = 6000
    url = f"{_API_BASE}/chart/foreign/item/{code}?periodType={period_type}&count={count}"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver_global history 실패 (%s): %s", stock_code, exc)
        return []

    infos = data.get("priceInfos", [])
    if not infos:
        return []

    rows = []
    for p in infos:
        date_str = p.get("localDate", "")
        if len(date_str) == 8:
            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        rows.append(
            {
                "date": date_str,
                "open": p.get("openPrice"),
                "high": p.get("highPrice"),
                "low": p.get("lowPrice"),
                "close": p.get("closePrice"),
                "volume": p.get("accumulatedTradingVolume"),
            }
        )

    # 날짜 범위 필터
    if start:
        rows = [r for r in rows if r["date"] >= start]
    if end:
        rows = [r for r in rows if r["date"] <= end]

    return rows
