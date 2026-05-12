"""네이버 글로벌 주식 — US/글로벌 주가 fallback (Yahoo 다음 2순위).

네이버 웹 스크래핑 (api.stock.naver.com). 공식 API 아님.
Reuters Code 체계: NASDAQ → .O, NYSE → 접미사 없음.

사용 시 주의:
    - **호출 간 2~4초 강제 딜레이** — 서버 보호 (asyncio.Lock으로 경쟁 방지)
    - Reuters Code 캐싱: 종목당 첫 호출만 5개 suffix 시도, 이후 캐시 히트
    - dayCandle 110개 하드 제한 → **endTime 페이징**으로 최대 1100일 수집
    - Yahoo v8 실패(429 rate limit) 시 이 모듈이 자동으로 이어받음

fallback 위치:
    yahoo_chart(1순위) → **naver_global(2순위)** → fmp(3순위)

데이터 범위:
    - dayCandle: 최대 ~1100일 (페이징 10회 × 110개)
    - weekCandle: ~2년
    - monthCandle: ~9년
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

# 서버 보호: 호출 간 2~4초 강제 딜레이 (모듈 전역)
_MIN_DELAY = 2.0
_MAX_DELAY = 4.0
_last_call_time: float = 0.0
_throttle_lock = asyncio.Lock()

# Reuters Code 캐시 — 종목당 5번 suffix 시도를 1번으로 줄임
_REUTERS_CACHE: dict[str, str | None] = {}


async def _throttle() -> None:
    """마지막 호출 이후 2~4초 대기 (Lock으로 경쟁 상태 방지).

    Returns
    -------
    None
        대기 완료 후 반환. _last_call_time 갱신.
    """
    global _last_call_time
    async with _throttle_lock:
        now = time.monotonic()
        elapsed = now - _last_call_time
        delay = random.uniform(_MIN_DELAY, _MAX_DELAY)
        if elapsed < delay:
            wait = delay - elapsed
            await asyncio.sleep(wait)
        _last_call_time = time.monotonic()


def _cleanNumber(val) -> float | None:
    """문자열/숫자 → float 변환. 콤마 제거 포함.

    Parameters
    ----------
    val
        변환할 값. str, int, float 또는 None.

    Returns
    -------
    float | None
        변환된 숫자. None이거나 변환 불가 시 None.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


async def _resolveReutersCode(ticker: str, client) -> str | None:
    """ticker → 네이버 Reuters Code (캐시 우선).

    Parameters
    ----------
    ticker : str
        종목 심볼 (예: "AAPL", "MSFT").
    client
        비동기 HTTP 클라이언트.

    Returns
    -------
    str | None
        매핑된 Reuters Code (예: "AAPL.O"). 실패 시 None.
    """
    if ticker in _REUTERS_CACHE:
        return _REUTERS_CACHE[ticker]

    for suffix in _SUFFIXES:
        await _throttle()
        code = f"{ticker}{suffix}"
        url = f"{_API_BASE}/stock/{code}/basic"
        try:
            resp = await client.get(url, headers={"Accept": "application/json"})
            data = resp.json()
            if data.get("stockName") and not data.get("code", "").startswith("Stock"):
                _REUTERS_CACHE[ticker] = code
                return code
        except (SourceUnavailableError, ValueError, KeyError):
            continue

    _REUTERS_CACHE[ticker] = None
    return None


async def fetchPrice(
    stockCode: str,
    client,
    *,
    market: str = "US",
    limit: int | None = None,
) -> PriceSnapshot | None:
    """네이버 글로벌 → 현재가 스냅샷.

    Parameters
    ----------
    stock_code : str
        종목 심볼 (예: ``"AAPL"``, ``"MSFT"``).
    client
        비동기 HTTP 클라이언트.
    market : str
        시장 코드. 기본값 ``"US"``.
    limit : int | None
        단건 PriceSnapshot 반환 함수라 무시된다. 인터페이스 호환 목적.

    Returns
    -------
    PriceSnapshot | None
        current : float — 현재가 (USD)
        change : float — 전일 대비 변동 (USD)
        change_pct : float — 전일 대비 변동률 (%)
        volume : int — 누적 거래량 (주)
        market_cap : float — 시가총액 (USD)
        source : str — ``"naver_global"``
        매핑 실패 또는 API 오류 시 None.

    Raises
    ------
    없음
        Naver global API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> snap = await fetchPrice("AAPL", client, market="US")
    """
    del limit
    code = await _resolveReutersCode(stockCode, client)
    if not code:
        log.warning("naver_global: %s 매핑 실패", stockCode)
        return None

    await _throttle()
    url = f"{_API_BASE}/stock/{code}/basic"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
        data = resp.json()
    except (SourceUnavailableError, ValueError) as exc:
        log.warning("naver_global price 실패 (%s): %s", stockCode, exc)
        return None

    current = _cleanNumber(data.get("closePrice"))
    if not current:
        return None

    change = _cleanNumber(data.get("compareToPreviousClosePrice")) or 0.0
    change_pct = _cleanNumber(data.get("fluctuationsRatio")) or 0.0
    volume = int(_cleanNumber(data.get("accumulatedTradingVolume")) or 0)

    # 시가총액 (억 달러 → 달러)
    marketCap = 0.0
    market_cap_raw = data.get("marketValue")
    if market_cap_raw:
        mc = _cleanNumber(market_cap_raw)
        if mc:
            marketCap = mc  # 네이버 API가 원단위로 줄 수 있음

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
        marketCap=marketCap,
        per=None,
        pbr=None,
        dividend_yield=None,
        source="naver_global",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        currency="USD",
        exchange=exchange_name,
        market=market,
    )


async def fetchHistory(
    stockCode: str,
    client,
    *,
    start: str = "",
    end: str = "",
    market: str = "US",
    limit: int | None = None,
    **kwargs,
) -> list[dict]:
    """네이버 글로벌 → OHLCV 히스토리.

    네이버 글로벌 chart API는 periodType별 110개 하드 제한.
    요청 기간에 따라 자동 선택:
      - 1년 이내: dayCandle (약 110 거래일 = 6개월)
      - 1~2년: weekCandle (약 110주 = 2년)
      - 2년 이상: monthCandle (약 110개월 = 9년)
    start 미지정이면 dayCandle (하위호환).

    Parameters
    ----------
    stock_code : str
        종목 심볼 (예: ``"AAPL"``, ``"MSFT"``).
    client
        비동기 HTTP 클라이언트.
    start : str
        시작일 (YYYY-MM-DD). 빈 문자열이면 필터 없음.
    end : str
        종료일 (YYYY-MM-DD). 빈 문자열이면 필터 없음.
    market : str
        시장 코드. 기본값 ``"US"``.
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 [start, end] 전체.

    Returns
    -------
    list[dict]
        OHLCV 행 목록 (날짜 오름차순, 중복 제거). 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - open : float — 시가 (USD)
        - high : float — 고가 (USD)
        - low : float — 저가 (USD)
        - close : float — 종가 (USD)
        - volume : int — 거래량 (주)

        매핑 실패 또는 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        Naver global chart API 내부 예외 (SourceUnavailableError/ValueError) 는 흡수.

    Example
    -------
    >>> rows = await fetchHistory("AAPL", client, start="2024-01-01")
    """
    code = await _resolveReutersCode(stockCode, client)
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

    # 페이징: dayCandle 110개 제한 → endTime으로 이전 데이터 반복 요청
    all_rows: list[dict] = []
    end_time = ""  # 빈 문자열 = 최신부터
    max_pages = 10 if period_type == "dayCandle" else 3

    for _page in range(max_pages):
        await _throttle()
        url = f"{_API_BASE}/chart/foreign/item/{code}?periodType={period_type}&count=500"
        if end_time:
            url += f"&endTime={end_time}"
        try:
            resp = await client.get(url, headers={"Accept": "application/json"})
            data = resp.json()
        except (SourceUnavailableError, ValueError) as exc:
            log.warning("naver_global history 실패 (%s): %s", stockCode, exc)
            break

        infos = data.get("priceInfos", [])
        if not infos:
            break

        page_rows: list[dict] = []
        for p in infos:
            dateStr = p.get("localDate", "")
            if len(dateStr) == 8:
                dateStr = f"{dateStr[:4]}-{dateStr[4:6]}-{dateStr[6:8]}"
            page_rows.append(
                {
                    "date": dateStr,
                    "open": p.get("openPrice"),
                    "high": p.get("highPrice"),
                    "low": p.get("lowPrice"),
                    "close": p.get("closePrice"),
                    "volume": p.get("accumulatedTradingVolume"),
                }
            )

        all_rows.extend(page_rows)

        # start 날짜 이전 데이터까지 도달했으면 중단
        if start and page_rows and page_rows[0]["date"] <= start:
            break

        # 다음 페이지: 현재 페이지의 가장 오래된 날짜를 endTime으로
        oldest = infos[0].get("localDate", "")
        if not oldest or oldest == end_time:
            break  # 더 이상 이전 데이터 없음
        end_time = oldest

    # 중복 제거 + 정렬
    seen: set[str] = set()
    unique_rows: list[dict] = []
    for r in all_rows:
        if r["date"] not in seen:
            seen.add(r["date"])
            unique_rows.append(r)
    unique_rows.sort(key=lambda r: r["date"])

    # 날짜 범위 필터
    if start:
        unique_rows = [r for r in unique_rows if r["date"] >= start]
    if end:
        unique_rows = [r for r in unique_rows if r["date"] <= end]

    if limit is not None and limit > 0:
        return unique_rows[-limit:]
    return unique_rows
