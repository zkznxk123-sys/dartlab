"""EDGAR prices stage — 회사별 일별 OHLCV bake (터미널 주가 그래프 artifact).

주가 그래프(PriceChart)는 회사별 일별 OHLCV 전체이력을 ``rt.price`` 포트로 백필한다. 본 스테이지는
gather US history(Yahoo v8 ~10년, 위임)를 ``edgar/prices/company/{ticker}.parquet`` 으로 구워
브라우저 터미널이 KR ``krx``/``gov`` 회사 주가와 동일 reader(``edgarPriceSource``)로 직독하게 한다.

별도빌드 금지 — 수집은 gather 에 위임(``gather.price(ticker, market="US")``). 본 모듈은 오케스트레이션
(유니버스 루프·parquet 쓰기·HF 증분 발행)만 한다. 온라인(Yahoo)이라 daily companyfacts(``edgar`` 스테이지)와
카덴스가 달라 별 스테이지로 둔다(KR ``buildGovPriceData`` 가 별 워크플로인 것과 동형).
"""

from __future__ import annotations

import time

from dartlab.pipeline.types import PipelineMode, StageResult

# date=Utf8 'YYYYMMDD' (Candle.t 규약). edgarPriceSource.parseEdgarPriceRows 가 대시 제거로 흡수하지만
# 정본을 8자리 문자열로 굳혀 브라우저(hyparquet) read 가 결정적이게 한다.
_START_DEFAULT = "2015-01-01"  # Yahoo 일봉 ~10년 — 그래프 전체이력(US 는 좌측 백필 없음, seed 가 곧 범위)


def _universeTickers() -> list[str]:
    """주가 bake 대상 유니버스 ticker(대문자) — edgarPanel 우선순위(상장 universe)와 동일 scope.

    Returns:
        list[str] — 중복 제거 ticker 목록. 부재 시 빈 목록(상위가 skip).
    """
    try:
        from dartlab.pipeline.stages.edgarPanel import _priorityTickers

        seen: dict[str, None] = {}
        for t in _priorityTickers():
            tk = str(t).strip().upper()
            if tk and tk not in seen:
                seen[tk] = None
        return list(seen)
    except Exception:  # noqa: BLE001 — 유니버스 산출 실패 → 빈 목록(skip, 빌드는 격리)
        return []


def _bakeOne(ticker: str, start: str, outDir) -> bool:
    """단일 ticker 의 US OHLCV 를 gather 위임으로 받아 parquet 으로 굽는다.

    Args:
        ticker: US 티커(대문자).
        start: 시작일 'YYYY-MM-DD'.
        outDir: 출력 디렉터리(Path).

    Returns:
        bool — 성공(파일 생성) True, 무데이터/실패 False.
    """
    import polars as pl

    from dartlab.gather import getDefaultGather

    df = getDefaultGather().price(ticker, market="US", start=start)
    if df is None or not hasattr(df, "height") or df.height == 0:
        return False
    # gather 출력 = [date(Date), open, high, low, close, volume]. date → Utf8 'YYYYMMDD'.
    dateExpr = (
        pl.col("date").dt.strftime("%Y%m%d")
        if df.schema.get("date") == pl.Date
        else pl.col("date").cast(pl.Utf8).str.replace_all("-", "")
    )
    out = df.with_columns(dateExpr.alias("date")).select(["date", "open", "high", "low", "close", "volume"])
    out = (
        out.filter(pl.col("date").str.contains(r"^\d{8}$") & pl.col("close").is_not_null())
        .sort("date")
        .unique(subset=["date"], keep="last")
    )
    if out.height == 0:
        return False
    out.write_parquet(outDir / f"{ticker}.parquet", compression="zstd", statistics=True)
    return True


def runEdgarPrices(
    *,
    category: str = "edgarPriceCompany",
    mode: PipelineMode = "recent",
    tickers: list[str] | None = None,
    start: str = _START_DEFAULT,
    limit: int | None = None,
    pauseSeconds: float = 0.0,
    upload: bool = True,
    token=None,
) -> StageResult:
    """유니버스 회사별 US OHLCV → ``edgar/prices/company/{ticker}.parquet`` bake + HF 증분 발행.

    수집은 gather(Yahoo, 429 백오프·fallback 체인 내장)에 위임한다. tickers 미지정이면 상장 universe
    전체(edgarPanel scope), 지정 시 그 목록만(스모크·증분). 개별 실패는 격리(나머지 진행).

    Args:
        category: HF 발행 카테고리(``edgarPriceCompany``).
        mode: 미사용(인터페이스 호환).
        tickers: bake 대상 ticker 목록(대문자 무관). None=유니버스 전체.
        start: OHLCV 시작일 'YYYY-MM-DD'.
        limit: 처리 ticker 수 상한(스모크·부분 실행). None=전체.
        pauseSeconds: ticker 간 대기(추가 페이싱 — gather 자체 백오프 위. 0=없음).
        upload: True 면 bake 변경분만 HF 증분 발행.
        token: HF 토큰(None=env).

    Returns:
        StageResult — ok=성공 ticker 수, err=실패 수.

    Raises:
        없음 — 개별 실패 격리.

    Example:
        >>> runEdgarPrices(tickers=["AAPL"], upload=False)  # doctest: +SKIP
        StageResult(category='edgarPriceCompany', ...)
    """
    from pathlib import Path

    import dartlab.config as cfg

    res = StageResult(category=category)
    uni = [str(t).strip().upper() for t in (tickers if tickers is not None else _universeTickers()) if str(t).strip()]
    if limit is not None:
        uni = uni[:limit]
    if not uni:
        print("[pipeline] edgarPrices: 대상 ticker 0 → skip", flush=True)
        res.report.skip += 1
        return res

    outDir = Path(cfg.dataDir) / "edgar" / "prices" / "company"
    outDir.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for i, ticker in enumerate(uni):
        try:
            if _bakeOne(ticker, start, outDir):
                changed.append(f"{ticker}.parquet")
                res.report.ok += 1
            else:
                res.report.skip += 1
        except Exception as exc:  # noqa: BLE001 — 개별 ticker 실패 격리
            res.report.err += 1
            res.report.failures.append(f"{ticker}: {type(exc).__name__}: {exc}")
            print(f"[pipeline] edgarPrices bake 실패({ticker}): {exc}", flush=True)
        if pauseSeconds and i + 1 < len(uni):
            time.sleep(pauseSeconds)

    print(f"[pipeline] edgarPrices: {res.report.ok}개 bake (대상 {len(uni)})", flush=True)
    if changed:
        from dartlab.pipeline.changed import writeChanged

        writeChanged(category, changed)
        if upload:
            from dartlab.pipeline.hfUpload import uploadCategoryToHf

            n = uploadCategoryToHf(category, changedFiles=changed, token=token)
            print(f"[pipeline] edgarPrices HF 발행: {n}개", flush=True)
    return res
