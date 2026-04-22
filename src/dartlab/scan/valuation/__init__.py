"""밸류에이션 횡단 스캔 -- PER/PBR/PSR + 등급 (네이버 실시간)."""

from __future__ import annotations

import asyncio

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

from dartlab.scan._helpers import scan_finance_parquets

_REVENUE_IDS = {"Revenue", "revenue", "ifrs-full_Revenue", "dart_Revenue"}
_REVENUE_NMS = {"매출액", "수익(매출액)", "영업수익"}

_CONCURRENCY = 50  # 동시 요청 제한


def _gradeValuation(pbr: float | None) -> str:
    """PBR 기준 밸류에이션 등급 분류.

    Parameters
    ----------
    pbr : float | None
        주가순자산비율 (배). None 또는 음수면 ``"해당없음"``.

    Returns
    -------
    grade : str
        밸류에이션 등급. 다음 중 하나:
        - ``"저평가"``   : 0 <= pbr < 0.5 (배)
        - ``"적정"``     : 0.5 <= pbr <= 1.5 (배)
        - ``"고평가"``   : 1.5 < pbr <= 3.0 (배)
        - ``"과열"``     : pbr > 3.0 (배)
        - ``"해당없음"`` : pbr 이 None 이거나 음수
    """
    if pbr is None:
        return "해당없음"
    if pbr < 0:
        return "해당없음"
    if pbr < 0.5:
        return "저평가"
    if pbr <= 1.5:
        return "적정"
    if pbr <= 3.0:
        return "고평가"
    return "과열"


async def _fetchAll(codes: list[str], verbose: bool) -> dict[str, dict]:
    """네이버 API 에서 종목별 시세·밸류에이션 지표를 비동기 배치 수집.

    Parameters
    ----------
    codes : list[str]
        수집 대상 종목코드 목록.
    verbose : bool
        True 이면 배치별 진행 상황을 stdout 에 출력.

    Returns
    -------
    dict[str, dict]
        종목코드를 키로 하는 dict. 각 값은 다음 키를 가진 dict:

        - marketCap : int — 시가총액 (원)
        - per : float | None — 주가수익비율 (배)
        - pbr : float | None — 주가순자산비율 (배)
        - dividendYield : float | None — 배당수익률 (%)
        - current : int — 현재가 (원)
    """
    import httpx

    from dartlab.gather.domains.naver import fetch_price

    result: dict[str, dict] = {}
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _fetch(code: str, client: httpx.AsyncClient) -> None:
        async with sem:
            try:
                snap = await fetch_price(code, client)
                if snap and snap.market_cap and snap.market_cap > 0:
                    result[code] = {
                        "marketCap": snap.market_cap,
                        "per": snap.per if snap.per else None,
                        "pbr": snap.pbr if snap.pbr else None,
                        "dividendYield": snap.dividend_yield if snap.dividend_yield else None,
                        "current": snap.current,
                    }
            except (httpx.HTTPError, ValueError, AttributeError):
                pass

    async with httpx.AsyncClient(timeout=10) as client:
        total = len(codes)
        batch = 200
        for i in range(0, total, batch):
            chunk = codes[i : i + batch]
            tasks = [_fetch(c, client) for c in chunk]
            await asyncio.gather(*tasks)
            if verbose:
                _log.info(f"  {min(i + batch, total)}/{total} 수집...")

    return result


def scanValuation(*, verbose: bool = True) -> pl.DataFrame:
    """전종목 밸류에이션 스캔 — PER/PBR/PSR + 등급 (**KR 전용**).

    네이버 API에서 실시간 수집. KR 2700종목 기준 2~3분 소요.

    AI 사용 가이드:
        - **KR 종목 컨텍스트에서만 호출**하라. US/글로벌 종목 분석 중에는 금지.
        - US 종목의 가치평가는 ``Company.analysis("가치평가")`` 또는
          ``quant("valuation", stockCode)`` 사용.
        - scan은 "전종목 횡단분석"이므로 단일 종목 분석에는 부적합.
          종목 1개 가치평가 목적이면 ``quant("value", stockCode)`` 호출.

    Returns
    -------
    pl.DataFrame
        stockCode/종목명/marketCap/per/pbr/psr/grade 컬럼. KR 2700종목.
    """
    if verbose:
        _log.info("밸류에이션 스캔: 상장사 목록 수집...")

    # 상장사 코드 목록
    import dartlab as _dl

    listing = _dl.listing()
    codes = listing["종목코드"].to_list() if "종목코드" in listing.columns else []
    if not codes:
        return pl.DataFrame()

    if verbose:
        _log.info(f"  {len(codes)}종목 → 네이버 API 수집 시작")

    # 매출 데이터 (PSR 계산용)
    revMap = scan_finance_parquets("IS", _REVENUE_IDS, _REVENUE_NMS)

    # async 수집
    priceMap = asyncio.run(_fetchAll(codes, verbose))

    if verbose:
        _log.info(f"  수집 완료: {len(priceMap)}종목")

    rows: list[dict] = []
    for code, data in priceMap.items():
        mc = data["marketCap"]
        per = data["per"]
        pbr = data["pbr"]
        dy = data["dividendYield"]

        # PSR = 시가총액(원) / 매출(원) — 둘 다 원 단위
        rev = revMap.get(code)
        psr = round(mc / rev, 2) if rev and rev > 0 and mc > 0 else None

        rows.append(
            {
                "stockCode": code,
                "marketCap": round(mc),
                "per": per,
                "pbr": pbr,
                "psr": psr,
                "dividendYield": dy,
                "grade": _gradeValuation(pbr),
            }
        )

    if verbose:
        _log.info(f"밸류에이션 스캔 완료: {len(rows)}종목")

    if not rows:
        return pl.DataFrame()

    schema = {
        "stockCode": pl.Utf8,
        "marketCap": pl.Float64,
        "per": pl.Float64,
        "pbr": pl.Float64,
        "psr": pl.Float64,
        "dividendYield": pl.Float64,
        "grade": pl.Utf8,
    }
    return pl.DataFrame(rows, schema=schema)


__all__ = ["scanValuation"]
