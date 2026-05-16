"""종합 기술적 분석 — 25개 지표 계산 + 판단(강세/중립/약세).

OHLCV DataFrame → 지표 DataFrame + 종합 판단 dict.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from dartlab.quant.signal import generator as sig
from dartlab.quant.signal._analyzerBenchmark import (
    _calcBeta,
    _categoryEdgeAudit,
    _fetchBenchmark,
    _relativeStrength,
)
from dartlab.quant.signal._analyzerCategories import (
    _categoryMomentum,
    _categoryPattern,
    _categoryTrend,
    _categoryVolatility,
    _categoryVolume,
)
from dartlab.synth import indicators as ind

__all_helpers__ = [
    "_calcBeta",
    "_categoryEdgeAudit",
    "_categoryMomentum",
    "_categoryPattern",
    "_categoryTrend",
    "_categoryVolatility",
    "_categoryVolume",
    "_fetchBenchmark",
    "_relativeStrength",
]


def enrichWithIndicators(df: pl.DataFrame) -> pl.DataFrame:
    """OHLCV DataFrame 에 기술적 지표 25 종을 컬럼으로 추가.

    Capabilities:
        가격 시계열 OHLCV 에 추세 (SMA/EMA/MACD/ADX/PSAR/Supertrend) + 모멘텀
        (RSI/Stochastic/ROC/Williams%R/CCI/CMO) + 변동성 (Bollinger/ATR/
        Keltner/Donchian) + 거래량 (OBV/MFI/Force Index/Elder Ray) 등 4 그룹
        25 지표를 모두 계산해 새 컬럼으로 추가. ``core/indicators`` SSOT 호출.

    Args:
        df: ``polars.DataFrame``. 필수 컬럼 ``date``/``open``/``high``/``low``/
            ``close``. ``volume`` 은 옵션 (없으면 0 으로 채움 → OBV/MFI 무효).

    Returns:
        ``pl.DataFrame`` — 원본 + 25 지표 컬럼 추가. 컬럼 명: ``sma20``/
        ``sma60``/``sma120``/``ema12``/``ema26``/``macd_line``/``macd_signal``/
        ``macd_hist``/``adx14``/``psar``/``supertrend``/``rsi14``/``stoch_k``/
        ``stoch_d``/``roc12``/``mom10``/``williamsR``/``cci20``/``cmo14``/
        ``bb_upper``/``bb_middle``/``bb_lower``/``atr14``/``obv``/``mfi14``.

    Example:
        >>> import polars as pl
        >>> from dartlab.quant import enrichWithIndicators
        >>> df = pl.read_parquet("price.parquet")  # OHLCV
        >>> enriched = enrichWithIndicators(df)
        >>> enriched.select(["close", "sma20", "rsi14", "macd_line"]).tail(5)

    Guide:
        ``technicalVerdict`` 의 사전 단계 — enrichWithIndicators 결과를
        verdict 함수가 소비. 단독으로도 chart / dashboard 용 widget 입력에 활용.
        지표 컬럼 일부만 필요해도 모두 계산되니, 대형 시리즈는 memory 주의.

    SeeAlso:
        - ``technicalVerdict``: 본 함수 결과 + 추가 진단
        - ``core.indicators.*``: 25 지표 본체 (vsma/vema/vrsi 등)
        - ``Quant`` 의 ``기술`` 축

    Requires:
        OHLCV polars DataFrame (252 일+ 권장 — SMA120/Bollinger 등 warmup
        고려). volume 없으면 거래량 계열 무효.

    AIContext:
        "이 종목 기술적 분석" · "차트 지표 보여줘" · "RSI/MACD 신호" 등
        가격 차트 분석 질문에 호출. 결과를 chart 또는 ``technicalVerdict``
        로 패스.

    LLM Specifications:
        AntiPatterns:
            - 252 일 미만 데이터로 호출 — sma120 / bb 워밍업 부족 NaN
            - volume 컬럼 없는데 OBV / MFI 인용 — 무효값 (전부 0)
            - 일자 정렬 안 됨 — date asc 필수 (호출 전 sort)
        OutputSchema:
            원본 컬럼 + 25 신규 컬럼 추가된 ``pl.DataFrame``. 모든 신규는
            float (NaN 가능). 컬럼 명 상기 참조.
        Prerequisites:
            polars 설치. 입력 df 가 OHLCV schema 일치. ``core.indicators``
            available.
        Freshness:
            입력 df 의 freshness 에 종속 (호출자 책임).
        Dataflow:
            df → numpy 추출 (close/high/low/volume) → 25 지표 계산 →
            with_columns 로 추가 → 반환.
        TargetMarkets: Global (가격 시계열 형식만 맞으면 KR/US/JP/등 모두).
    """
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)
    volume = df["volume"].to_numpy().astype(np.float64) if "volume" in df.columns else np.zeros(len(close))

    # 추세
    sma20 = ind.vsma(close, 20)
    sma60 = ind.vsma(close, 60)
    sma120 = ind.vsma(close, 120)
    ema12 = ind.vema(close, 12)
    ema26 = ind.vema(close, 26)
    macd_line, macd_signal, macd_hist = ind.vmacd(close)
    adx14 = ind.vadx(high, low, close, 14)
    psar = ind.vpsar(high, low)
    st, st_dir = ind.vsupertrend(high, low, close)

    # 모멘텀
    rsi14 = ind.vrsi(close, 14)
    stoch_k, stoch_d = ind.vstochastic(high, low, close)
    roc12 = ind.vroc(close, 12)
    mom10 = ind.vmomentum(close, 10)
    willR = ind.vwilliamsR(high, low, close, 14)
    cci20 = ind.vcci(high, low, close, 20)
    cmo14 = ind.vcmo(close, 14)

    # 변동성
    bb_upper, bb_middle, bb_lower = ind.vbollinger(close, 20, 2.0)
    atr14 = ind.vatr(high, low, close, 14)
    kelt_upper, kelt_middle, kelt_lower = ind.vkeltner(high, low, close)
    don_upper, don_middle, don_lower = ind.vdonchian(high, low, 20)

    # 거래량
    obv = ind.vobv(close, volume)
    mfi14 = ind.vmfi(high, low, close, volume, 14)
    force13 = ind.vforceIndex(close, volume, 13)
    bull, bear = ind.velderRay(high, low, close, 13)

    return df.with_columns(
        [
            # 추세
            pl.Series("sma20", sma20),
            pl.Series("sma60", sma60),
            pl.Series("sma120", sma120),
            pl.Series("ema12", ema12),
            pl.Series("ema26", ema26),
            pl.Series("macd", macd_line),
            pl.Series("macdSignal", macd_signal),
            pl.Series("macdHist", macd_hist),
            pl.Series("adx", adx14),
            pl.Series("psar", psar),
            pl.Series("supertrend", st),
            pl.Series("stDirection", st_dir),
            # 모멘텀
            pl.Series("rsi", rsi14),
            pl.Series("stochK", stoch_k),
            pl.Series("stochD", stoch_d),
            pl.Series("roc", roc12),
            pl.Series("momentum", mom10),
            pl.Series("williamsR", willR),
            pl.Series("cci", cci20),
            pl.Series("cmo", cmo14),
            # 변동성
            pl.Series("bbUpper", bb_upper),
            pl.Series("bbLower", bb_lower),
            pl.Series("atr", atr14),
            pl.Series("keltUpper", kelt_upper),
            pl.Series("keltLower", kelt_lower),
            pl.Series("donchianUpper", don_upper),
            pl.Series("donchianLower", don_lower),
            # 거래량
            pl.Series("obv", obv),
            pl.Series("mfi", mfi14),
            pl.Series("forceIndex", force13),
            pl.Series("bullPower", bull),
            pl.Series("bearPower", bear),
        ]
    )


def technicalVerdict(
    df: pl.DataFrame,
    *,
    stockCode: str | None = None,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
) -> dict[str, Any]:
    """OHLCV → 종합 기술적 판단 (강세 / 중립 / 약세 verdict + 다중 신호).

    Capabilities:
        가격 시계열에서 RSI/SMA/Bollinger/ADX 등 핵심 지표를 합산해 종합
        verdict 산출. score (-4~+4) 와 함께 ``강세`` / ``중립`` / ``약세``
        라벨 반환. 벤치마크 (시장 지수 또는 동종 업종) 와의 상대 강도 옵션.

    Args:
        df: ``polars.DataFrame`` (OHLCV — date/open/high/low/close/volume).
        stockCode: 종목 코드 (옵션). 결과 dict 에 포함.
        market: ``"auto"`` (기본) / ``"KR"`` / ``"US"``. 벤치마크 자동 선택용.
        benchmark: 벤치마크 종목 코드 (예 ``"KOSPI"``, ``"SPY"``). None 이면
            market 자동.
        benchmarkMode: ``"market"`` (기본, 시장 지수) 또는 ``"sector"`` (업종).

    Returns:
        dict — ``verdict`` (str) / ``score`` (int, -4~+4) / ``rsi`` (float) /
        ``aboveSma20`` (bool|None) / ``aboveSma60`` (bool|None) / ``bbPosition``
        (str) / ``adx`` (float|None) / ``signals`` (list[str]) /
        ``relativeStrength`` (dict|None, benchmark 지정 시) 등.

    Example:
        >>> import polars as pl
        >>> from dartlab.quant import technicalVerdict
        >>> df = pl.read_parquet("price.parquet")
        >>> r = technicalVerdict(df, stockCode="005930", market="KR")
        >>> r["verdict"], r["score"]
        ('강세', 3)

    Guide:
        score = 다중 지표 가중 합 — RSI > 70 / SMA 정배열 / Bollinger 상단 /
        ADX > 25 (강한 추세) 등 강세 신호 +1 씩, 반대 -1 씩. 절대값 의존 금지
        — signals list 의 근거 함께 인용. macro 사이클 + 본 verdict 교차 해석.

    SeeAlso:
        - ``enrichWithIndicators``: 25 지표 컬럼 추가 (full set)
        - ``Quant`` 의 ``기술`` 축
        - ``calcMomentum`` / ``calcVolatility``: 단일 그룹 깊이 분석

    Requires:
        OHLCV polars DataFrame, 252 일+ 권장 (SMA60 warmup). 벤치마크 사용 시
        동일 기간 벤치마크 시계열 가용성.

    AIContext:
        "이 종목 기술적으로 강세인가" · "RSI 과매수 / 과매도" · "200 일선
        뚫었나" 등 차트 단기 진단 질문에 호출. verdict + signals 함께 인용.

    LLM Specifications:
        AntiPatterns:
            - verdict 만 인용 (score / signals 무시) — 같은 verdict 도 신호
              내용이 다름
            - 1 일치 verdict 만 보고 매매 단정 — 추세 (5/20 일 verdict 시계열)
              검토 권장
            - benchmark 없이 relativeStrength 기대 — None 반환
        OutputSchema:
            ``{verdict: str, score: int, rsi: float, aboveSma20: bool|None,
            aboveSma60: bool|None, bbPosition: str, adx: float|None,
            signals: list[str], relativeStrength: dict|None}``.
        Prerequisites:
            OHLCV 시계열 + (옵션) 벤치마크 시계열. polars + numpy.
        Freshness:
            입력 df 의 latest date 에 종속 — 호출자 책임.
        Dataflow:
            df → 지표 4 종 계산 → 각 신호 +/- 1 합산 → score → verdict
            (강세 ≥+2 / 중립 / 약세 ≤-2) → dict.
        TargetMarkets: Global (KR/US/JP 모두). market 인자로 벤치마크 라우팅.
    """
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)

    rsi = ind.vrsi(close, 14)
    sma20 = ind.vsma(close, 20)
    sma60 = ind.vsma(close, 60)
    bb_upper, _, bb_lower = ind.vbollinger(close)
    adx = ind.vadx(high, low, close)

    # 현재 값
    last_rsi = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0
    last_close = float(close[-1])
    above20 = bool(last_close > sma20[-1]) if not np.isnan(sma20[-1]) else None
    above60 = bool(last_close > sma60[-1]) if not np.isnan(sma60[-1]) else None
    last_adx = float(adx[-1]) if not np.isnan(adx[-1]) else None

    # BB 위치
    bb_pos = None
    if not np.isnan(bb_upper[-1]) and not np.isnan(bb_lower[-1]):
        rng = bb_upper[-1] - bb_lower[-1]
        if rng > 0:
            bb_pos = round((last_close - bb_lower[-1]) / rng * 100, 1)

    # 점수 (-4 ~ +4)
    score = 0
    if last_rsi < 30:
        score += 2
    elif last_rsi < 40:
        score += 1
    elif last_rsi > 70:
        score -= 2
    elif last_rsi > 60:
        score -= 1
    if above20:
        score += 1
    elif above20 is not None:
        score -= 1
    if above60:
        score += 1
    elif above60 is not None:
        score -= 1

    if score >= 2:
        verdict = "강세"
    elif score <= -2:
        verdict = "약세"
    else:
        verdict = "중립"

    # 최근 20일 신호
    golden = sig.vgoldenCross(close, fast=20, slow=60)
    rsi_sig = sig.vrsiSignal(rsi)
    macd_sig = sig.vmacdSignal(close)
    recent = min(20, len(close))

    result = {
        "verdict": verdict,
        "score": score,
        "rsi": round(last_rsi, 1),
        "adx": round(last_adx, 1) if last_adx else None,
        "aboveSma20": above20,
        "aboveSma60": above60,
        "bbPosition": bb_pos,
        "signals": {
            "goldenCross": int(golden[-recent:].sum()),
            "rsiSignal": int(rsi_sig[-recent:].sum()),
            "macdSignal": int(macd_sig[-recent:].sum()),
        },
    }

    # 시장 대비 상대강도 + 베타 (가능하면)
    try:
        bench_result = _fetchBenchmark(
            benchmark or "KOSPI",
            stockCode=stockCode,
            market=market,
            benchmarkMode=benchmarkMode,
            returnMeta=True,
        )
        if isinstance(bench_result, tuple):
            marketDf, benchmark_meta = bench_result
        else:
            marketDf, benchmark_meta = bench_result, None
        if marketDf is not None and not marketDf.is_empty():
            rs = _relativeStrength(df, marketDf)
            beta = _calcBeta(df, marketDf)
            result["relativeStrength"] = rs
            result["beta"] = beta
            if benchmark_meta:
                result["benchmarkUsed"] = benchmark_meta
    except (ValueError, KeyError, AttributeError, ZeroDivisionError):
        pass

    # ── 카테고리 분해 (Phase 5 verdict 강화 + 12년 audit 검증) ──
    #
    # 12년 audit 결과 (5종목 2014~2026, Welch's t-test α=0.05):
    #   trend 강한상승: t=7.63@20d ✅ (12년 강건)
    #   trend 횡보:     t=-6.26@20d ✅ (12년 강건)
    #   trend 약한상승/약한하락: ❌ t 부족
    #   momentum 전부: ❌ 12년에서 모든 라벨 fail (5년 과적합)
    #   volatility 전부: ❌ 12년에서 모든 라벨 fail (5년 과적합)
    #   volume/pattern: ❌ 5년에서도 fail
    #
    # 결론: trend 만 유지, 2분류 (강한 상승 / 그 외)
    # momentum/volatility indicators 는 verdict dict 최상위에 이미 노출 (rsi/adx/bbPosition)
    result["categories"] = {
        "trend": _categoryTrend(close, high, low),
    }

    return result
