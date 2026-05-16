"""시장 미시구조 분석 — Amihud 비유동성, Roll 스프레드, 회전율.

학술 근거:
- Amihud (2002): Illiquidity and stock returns
- Roll (1984): A simple implicit measure of the effective bid-ask spread
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def calcLiquidity(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """시장 미시구조 유동성 분석 — Amihud + Roll + 회전율.

    Capabilities:
        Amihud (2002) ILLIQ = mean(|r| / dollar_volume) + log scale +
        recent 20d 변화 추적 + Roll (1984) effective spread = 2 √(-cov(Δp,
        Δp_{t-1})) + turnover (회전율) → liquidityGrade (A~F) 라벨.
        대형주 vs 소형주 유동성 차이 정량화.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".

    Returns:
        dict:
            - ``amihud``/``amihudLog`` (float): 비유동성 (높을수록 비유동).
            - ``rollSpread`` (float): 추정 effective spread.
            - ``turnover`` (float): 회전율.
            - ``liquidityGrade`` (str): A~F.
            - 또는 ``error`` (str): 20 일 미만.

    Raises:
        없음 (error 키).

    Example:
        >>> r = calcLiquidity("005930")
        >>> r["amihudLog"], r["liquidityGrade"]
        (-8.5, 'A')  # 대형주 → A 등급

    Guide:
        - amihud > 1e-6 = 비유동 (소형주). 1e-9 미만 = 매우 유동 (대형주).
        - rollSpread 가 명시적 bid-ask 보다 크면 noisy trade (저유동).
        - 펀드 운용 시 일일 거래량의 5~10% 이내 매매 권장 → amihud 가
          impact cost 추정 입력.

    SeeAlso:
        - ``calcVolume``: 거래량 흐름
        - ``calcVolatility``: vol (저유동주는 vol 큼)
        - ``screen``: 유동성 필터 (펀드 스크리닝)

    Requires:
        OHLCV (close + volume) ≥ 20 일.

    AIContext:
        liquidityGrade 단독 인용 금지 — amihudLog 절대값 + 비교 universe 명시.
        US 대형주 (AAPL, MSFT) vs KR 대형주 amihud 절대값은 시장 규모 차이로
        직접 비교 어려움.

    LLM Specifications:
        AntiPatterns:
            - amihud 절대값 KR↔US 직접 비교 — 시장 규모 차이.
            - 20 일 미만에 본 함수 호출 — error.
        OutputSchema:
            ``{amihud: float, amihudLog: float, rollSpread: float, turnover:
              float, liquidityGrade: str}``.
        Prerequisites:
            OHLCV close + volume ≥ 20 일.
        Freshness:
            일별.
        Dataflow:
            OHLCV → daily return + dollar volume → Amihud → Roll covariance
            → turnover → grade.
        TargetMarkets: KR (KRX), US (NYSE/NASDAQ).
    """
    market = resolveMarket(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
    close = arr.get("close")
    volume = arr.get("volume")

    if close is None or volume is None or len(close) < 20:
        return {"error": f"{stockCode} 데이터 부족"}

    n = len(close)
    daily_returns = np.diff(close) / close[:-1]

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "dataPoints": n,
    }

    # ── Amihud Illiquidity Ratio (2002) ──
    # ILLIQ = (1/D) * Σ |r_t| / Volume_t
    # 높을수록 비유동적
    dollar_volume = close[1:] * volume[1:]
    valid = dollar_volume > 0
    if np.sum(valid) > 0:
        illiq_daily = np.abs(daily_returns[valid]) / dollar_volume[valid]
        amihud = float(np.mean(illiq_daily))
        # 로그 스케일로 해석 편의
        amihud_log = float(np.log10(amihud + 1e-20))

        result["amihud"] = amihud
        result["amihudLog"] = round(amihud_log, 4)

        # 최근 20일 vs 전체 비교 (유동성 변화 감지)
        if n > 40:
            recent = np.abs(daily_returns[-20:]) / dollar_volume[-20:]
            recent_valid = dollar_volume[-20:] > 0
            if np.sum(recent_valid) > 0:
                amihud_recent = float(np.mean(recent[recent_valid]))
                amihud_change = (amihud_recent - amihud) / amihud if amihud > 0 else 0
                result["amihudRecent"] = amihud_recent
                result["liquidityChange"] = (
                    "악화" if amihud_change > 0.2 else "개선" if amihud_change < -0.2 else "유지"
                )

    # ── Roll Spread (1984) ──
    # S = 2 * sqrt(-Cov(ΔP_t, ΔP_{t-1}))
    # 유효한 경우에만 (공분산이 음수일 때)
    if len(daily_returns) >= 20:
        price_changes = np.diff(close)
        if len(price_changes) >= 2:
            cov = float(np.cov(price_changes[1:], price_changes[:-1])[0, 1])
            if cov < 0:
                roll_spread = 2 * np.sqrt(-cov)
                # 가격 대비 비율
                avg_price = float(np.mean(close[-20:]))
                roll_pct = roll_spread / avg_price * 100 if avg_price > 0 else 0
                result["rollSpread"] = round(float(roll_spread), 4)
                result["rollSpreadPct"] = round(roll_pct, 4)
            else:
                result["rollSpread"] = 0
                result["rollSpreadPct"] = 0
                result["rollNote"] = "양의 자기상관 (Roll 모델 비적용)"

    # ── 회전율 (Turnover Ratio) ──
    # 일평균 거래량 / 시가총액 근사
    if n >= 20:
        avg_volume_20 = float(np.mean(volume[-20:]))
        avg_volume_60 = float(np.mean(volume[-min(60, n) :])) if n >= 60 else float(np.mean(volume))
        result["avgVolume20d"] = round(avg_volume_20, 0)
        result["avgVolume60d"] = round(avg_volume_60, 0)

        # 거래량 변동계수 (CV) — 유동성 안정성
        vol_std = float(np.std(volume[-60:] if n >= 60 else volume))
        vol_cv = vol_std / avg_volume_60 if avg_volume_60 > 0 else 0
        result["volumeCV"] = round(vol_cv, 4)

    # ── 가격 충격 추정 (Kyle Lambda 근사) ──
    # λ ≈ |Δprice| / volume (단순 근사)
    if len(daily_returns) >= 20 and np.sum(volume[1:] > 0) > 0:
        valid_vol = volume[1:] > 0
        lambda_daily = np.abs(daily_returns[valid_vol]) / np.sqrt(volume[1:][valid_vol])
        kyle_lambda = float(np.median(lambda_daily))
        result["kyleLambda"] = kyle_lambda

    # ── 제로거래 비율 ──
    # 거래량 0인 날의 비율 — 높으면 극도로 비유동적
    zero_days = int(np.sum(volume == 0))
    result["zeroDays"] = zero_days
    result["zeroRatio"] = round(zero_days / n, 4)

    # ── 유동성 등급 ──
    grade_score = 0
    # Amihud 기준
    if "amihudLog" in result:
        alog = result["amihudLog"]
        if alog < -10:
            grade_score += 3  # 매우 유동적
        elif alog < -8:
            grade_score += 2
        elif alog < -6:
            grade_score += 1
        # -6 이상이면 0 (비유동적)

    # Roll spread 기준
    if "rollSpreadPct" in result:
        rsp = result["rollSpreadPct"]
        if rsp < 0.1:
            grade_score += 2
        elif rsp < 0.5:
            grade_score += 1

    # 거래량 기준
    if "volumeCV" in result:
        cv = result["volumeCV"]
        if cv < 0.5:
            grade_score += 1  # 안정적

    if "zeroRatio" in result and result["zeroRatio"] > 0.1:
        grade_score -= 2  # 거래 없는 날 많으면 감점

    if grade_score >= 5:
        result["liquidityGrade"] = "A"
    elif grade_score >= 3:
        result["liquidityGrade"] = "B"
    elif grade_score >= 1:
        result["liquidityGrade"] = "C"
    else:
        result["liquidityGrade"] = "D"

    return result
